"""
Serialização determinística de ASTs para uso no Meta-LER.
"""

from __future__ import annotations

import ast
from collections import Counter
from dataclasses import dataclass, field
from typing import Iterable

from liu import Node, entity, struct as liu_struct, list_node, text as liu_text, number, boolean

MAX_AST_NODES = 512
MAX_LITERAL_PREVIEW = 80


@dataclass(slots=True)
class _AstTracker:
    max_nodes: int = MAX_AST_NODES
    count: int = 0
    truncated: bool = False
    type_counts: Counter = field(default_factory=Counter)

    def note(self, node: ast.AST) -> bool:
        self.count += 1
        if self.count > self.max_nodes:
            self.truncated = True
            return False
        self.type_counts[type(node).__name__] += 1
        return True


def build_python_ast_meta(source: str) -> Node | None:
    """
    Converte código Python em um STRUCT LIU que representa o AST.
    """

    try:
        tree = ast.parse(source)
    except SyntaxError:
        return None
    tracker = _AstTracker()
    root = _convert_node(tree, tracker, None)
    summary = _summary_nodes(tracker.type_counts)
    fields = {
        "tag": entity("code_ast"),
        "language": entity("python"),
        "node_count": number(tracker.count),
        "root": root,
    }
    if summary:
        fields["summary"] = list_node(summary)
    if tracker.truncated:
        fields["truncated"] = boolean(True)
    return liu_struct(**fields)


def _convert_node(node: ast.AST, tracker: _AstTracker, field_name: str | None) -> Node:
    if not tracker.note(node):
        return liu_struct(tag=entity("ast_truncated"))
    child_nodes = []
    literal_fields = []
    for name, value in ast.iter_fields(node):
        if isinstance(value, ast.AST):
            child_nodes.append(_convert_node(value, tracker, name))
        elif isinstance(value, list):
            child_nodes.extend(_convert_list(name, value, tracker))
        elif value is not None:
            literal_fields.append(_literal_field(name, value))
    data = {
        "tag": entity("ast"),
        "type": entity(type(node).__name__),
    }
    if field_name:
        data["field"] = entity(field_name)
    if literal_fields:
        data["fields"] = list_node(literal_fields)
    if child_nodes:
        data["children"] = list_node(child_nodes)
    return liu_struct(**data)


def _convert_list(field_name: str, values: Iterable[object], tracker: _AstTracker):
    nodes = []
    for value in values:
        if isinstance(value, ast.AST):
            nodes.append(_convert_node(value, tracker, field_name))
        elif value is not None:
            nodes.append(
                liu_struct(
                    tag=entity("ast_literal"),
                    field=entity(field_name),
                    value=liu_text(_literal_preview(value)),
                )
            )
    return nodes


def _literal_field(name: str, value: object) -> Node:
    return liu_struct(tag=entity("ast_field"), name=entity(name), value=liu_text(_literal_preview(value)))


def _literal_preview(value: object) -> str:
    text_value = repr(value)
    if len(text_value) > MAX_LITERAL_PREVIEW:
        return text_value[: MAX_LITERAL_PREVIEW - 3] + "..."
    return text_value


def build_rust_ast_meta(functions: list[dict], source: str) -> Node:
    return _build_outline_code_ast("rust", functions, source)


def build_js_ast_meta(functions: list[dict], source: str) -> Node:
    return _build_outline_code_ast("javascript", functions, source)


def build_elixir_ast_meta(functions: list[dict], source: str) -> Node:
    return _build_outline_code_ast("elixir", functions, source)


def _build_outline_code_ast(language: str, functions: list[dict], source: str) -> Node:
    fn_nodes = []
    for item in functions:
        params = [
            liu_struct(
                tag=entity("code_param"),
                name=entity(param["name"]),
                type=liu_text(param.get("type", "")),
            )
            for param in item.get("params", [])
        ]
        fn_nodes.append(
            liu_struct(
                tag=entity("code_fn_outline"),
                name=entity(item["name"]),
                params=list_node(params),
                param_count=number(len(params)),
                ret=liu_text(item.get("ret", "")),
                body=liu_text(item.get("body", "")),
            )
        )
    return liu_struct(
        tag=entity("code_ast"),
        language=entity(language),
        node_count=number(len(functions)),
        functions=list_node(fn_nodes),
        preview=liu_text(_preview_source(source)),
    )


def _preview_source(source: str, limit: int = 160) -> str:
    compact = " ".join(source.strip().split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 3] + "..."


def _summary_nodes(counter: Counter) -> list[Node]:
    most_common = counter.most_common(8)
    nodes = []
    for name, count in most_common:
        nodes.append(liu_struct(tag=entity("ast_type"), name=entity(name), count=number(count)))
    return nodes


__all__ = [
    "build_python_ast_meta",
    "build_rust_ast_meta",
    "build_js_ast_meta",
    "build_elixir_ast_meta",
]
