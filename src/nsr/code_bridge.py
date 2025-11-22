"""
Code bridge – detecta snippets Python determinísticos e os converte em LIU.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Tuple

from liu import Node, entity, struct as liu_struct, text as liu_text, list_node, number, relation

from frontend_python.compiler import compile_source
from frontend_rust.compiler import compile_items as compile_rust_items
from .code_ast import (
    build_python_ast_meta,
    build_rust_ast_meta,
    build_js_ast_meta,
    build_elixir_ast_meta,
)


@dataclass(frozen=True, slots=True)
class CodeHook:
    """Acoplamento determinístico entre código-fonte e LIU."""

    language: str
    module: str
    struct_node: Node
    answer_node: Node
    context_nodes: Tuple[Node, ...]
    quality: float
    trace_label: str
    ast_node: Node | None = None


PYTHON_KEYWORDS = (
    "def ",
    "class ",
    "async def ",
    "from ",
    "import ",
    "@",
    "if __name__",
)

RUST_FN_PATTERN = re.compile(
    r"fn\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(([^)]*)\)\s*(?:->\s*([A-Za-z0-9_<>&\[\]:]+))?",
    re.MULTILINE,
)


def maybe_route_code(text_value: str, module_name: str = "input", dialect: str | None = None) -> CodeHook | None:
    """Detecta código determinístico e devolve o pacote LIU correspondente."""

    normalized = (dialect or "").lower()
    if normalized.startswith("rust"):
        return _maybe_route_rust(text_value, module_name)
    if normalized.startswith("javascript") or normalized.startswith("js"):
        return _maybe_route_outline(
            text_value,
            module_name,
            language="javascript",
            extractor=_extract_js_functions,
            ast_builder=build_js_ast_meta,
            trace_label="CODE[JS]",
        )
    if normalized.startswith("elixir"):
        return _maybe_route_outline(
            text_value,
            module_name,
            language="elixir",
            extractor=_extract_elixir_functions,
            ast_builder=build_elixir_ast_meta,
            trace_label="CODE[ELIXIR]",
        )
    if normalized and not normalized.startswith("python"):
        return None
    if not _looks_like_python(text_value):
        return None
    try:
        relations = tuple(compile_source(text_value, module=module_name))
    except SyntaxError:
        return None
    if not relations:
        return None
    struct_node = _build_struct(relations, module_name, "python")
    answer_node = _build_answer(relations, module_name, "python")
    ast_node = build_python_ast_meta(text_value)
    context_nodes = _build_context(relations, module_name, ast_node, "python")
    return CodeHook(
        language="code/python",
        module=module_name,
        struct_node=struct_node,
        answer_node=answer_node,
        context_nodes=context_nodes,
        quality=0.88,
        trace_label="CODE[PYTHON]",
        ast_node=ast_node,
    )


def _looks_like_python(text_value: str) -> bool:
    stripped = text_value.lstrip()
    if len(stripped) < 6:
        return False
    first_line = stripped.splitlines()[0].strip()
    lowered = first_line.lower()
    for keyword in PYTHON_KEYWORDS:
        if lowered.startswith(keyword.strip().lower()) or keyword in stripped:
            return True
    return any(ch in stripped for ch in (":", "()", "->")) and "def " in stripped


def _maybe_route_rust(text_value: str, module_name: str) -> CodeHook | None:
    items = _extract_rust_functions(text_value)
    if not items:
        return None
    relations = tuple(compile_rust_items(module_name, items))
    if not relations:
        return None
    struct_node = _build_struct(relations, module_name, "rust")
    answer_node = _build_answer(relations, module_name, "rust")
    ast_node = build_rust_ast_meta(items, text_value)
    context_nodes = _build_context(relations, module_name, ast_node, "rust")
    return CodeHook(
        language="code/rust",
        module=module_name,
        struct_node=struct_node,
        answer_node=answer_node,
        context_nodes=context_nodes,
        quality=0.82,
        trace_label="CODE[RUST]",
        ast_node=ast_node,
    )


def _maybe_route_outline(
    text_value: str,
    module_name: str,
    *,
    language: str,
    extractor,
    ast_builder,
    trace_label: str,
) -> CodeHook | None:
    items = extractor(text_value)
    if not items:
        return None
    relations = tuple(_outline_relations(language, module_name, items))
    if not relations:
        return None
    struct_node = _build_struct(relations, module_name, language)
    answer_node = _build_answer(relations, module_name, language)
    ast_node = ast_builder(items, text_value)
    context_nodes = _build_context(relations, module_name, ast_node, language)
    return CodeHook(
        language=f"code/{language}",
        module=module_name,
        struct_node=struct_node,
        answer_node=answer_node,
        context_nodes=context_nodes,
        quality=0.8,
        trace_label=trace_label,
        ast_node=ast_node,
    )


def _build_struct(relations: Tuple[Node, ...], module_name: str, language: str) -> Node:
    return liu_struct(
        tag=entity("code_struct"),
        language=entity(language),
        module=entity(module_name),
        relations=list_node(list(relations)),
    )


def _build_answer(relations: Tuple[Node, ...], module_name: str, language: str) -> Node:
    fn_count = sum(1 for rel in relations if (rel.label or "").startswith("code/DEFN"))
    summary = f"Módulo {language} {module_name} com {fn_count} definições e {len(relations)} relações LIU."
    return liu_struct(
        tag=entity("code_summary"),
        answer=liu_text(summary),
        plan_role=entity("code_summary"),
        plan_language=entity("pt"),
    )


def _build_context(
    relations: Tuple[Node, ...], module_name: str, ast_node: Node | None, language: str
) -> Tuple[Node, ...]:
    context: list[Node] = [
        liu_struct(
            tag=entity("code_stats"),
            language=entity(language),
            module=entity(module_name),
            relations=number(len(relations)),
            definitions=number(sum(1 for rel in relations if (rel.label or "").startswith("code/DEFN"))),
        )
    ]
    for rel in relations[:3]:
        context.append(
            liu_struct(
                tag=entity("code_relation"),
                label=entity(rel.label or ""),
                preview=liu_text(_preview_relation(rel)),
            )
        )
    if ast_node is not None:
        context.append(ast_node)
    return tuple(context)


def _preview_relation(rel: Node) -> str:
    subject = rel.args[0].label if rel.args else ""
    obj = rel.args[1].label if len(rel.args) > 1 else ""
    if subject and obj:
        return f"{rel.label}({subject}, {obj})"
    if subject:
        return f"{rel.label}({subject})"
    return rel.label or "REL"


def _extract_rust_functions(source: str) -> list[dict]:
    items = []
    for match in RUST_FN_PATTERN.finditer(source):
        name = match.group(1)
        params_segment = match.group(2) or ""
        ret_type = (match.group(3) or "").strip()
        params = _parse_rust_params(params_segment)
        body_preview = _rust_body_preview(source, match.end())
        items.append(
            {
                "kind": "fn",
                "name": name,
                "params": params,
                "ret": ret_type,
                "body": body_preview,
            }
        )
    return items


def _parse_rust_params(segment: str) -> list[dict]:
    params = []
    for raw in segment.split(","):
        token = raw.strip()
        if not token:
            continue
        name, _, type_part = token.partition(":")
        params.append({"name": name.strip(), "type": type_part.strip()})
    return params


def _rust_body_preview(source: str, start_index: int, limit: int = 200) -> str:
    remainder = source[start_index:].lstrip()
    snippet = remainder.split("}", 1)[0] if "}" in remainder else remainder
    compact = " ".join(snippet.strip().split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 3] + "..."


def _extract_js_functions(source: str) -> list[dict]:
    pattern = re.compile(
        r"function\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(([^)]*)\)\s*\{(.*?)\}",
        re.DOTALL,
    )
    items = []
    for match in pattern.finditer(source):
        name = match.group(1)
        params = _parse_generic_params(match.group(2))
        body = " ".join(match.group(3).strip().split())
        items.append({"name": name, "params": params, "body": body, "ret": ""})
    return items


def _extract_elixir_functions(source: str) -> list[dict]:
    pattern = re.compile(
        r"defp?\s+([a-zA-Z0-9_!?]+)\s*\(([^)]*)\)\s+do(.*?)end",
        re.DOTALL,
    )
    items = []
    for match in pattern.finditer(source):
        name = match.group(1)
        params = _parse_generic_params(match.group(2))
        body = " ".join(match.group(3).strip().split())
        items.append({"name": name, "params": params, "body": body, "ret": ""})
    return items


def _parse_generic_params(segment: str) -> list[dict]:
    params = []
    for raw in segment.split(","):
        token = raw.strip()
        if not token:
            continue
        if ":" in token:
            name, _, type_part = token.partition(":")
            params.append({"name": name.strip(), "type": type_part.strip()})
        else:
            params.append({"name": token, "type": ""})
    return params


def _outline_relations(language: str, module_name: str, items: list[dict]) -> list[Node]:
    rels = []
    for item in items:
        fn_entity = entity(f"code/fn::{language}::{module_name}::{item['name']}")
        params = [
            struct(tag=entity("code_param"), name=entity(param["name"]), type=text(param.get("type", "")))
            for param in item.get("params", [])
        ]
        fn_struct = struct(
            tag=entity("code_fn_outline"),
            language=entity(language),
            module=entity(module_name),
            name=entity(item["name"]),
            params=list_node(params),
            param_count=number(len(params)),
            ret=text(item.get("ret", "")),
            body=text(item.get("body", "")),
        )
        rels.append(relation("code/DEFN", fn_entity, fn_struct))
        for param_struct in params:
            rels.append(relation("code/PARAM", fn_entity, param_struct))
    return rels


__all__ = ["CodeHook", "maybe_route_code"]
