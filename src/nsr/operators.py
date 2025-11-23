"""
Operadores Φ do NSR.
"""

from __future__ import annotations

import math
from collections import deque
from typing import Callable, Dict, Iterable, Tuple

from liu import (
    Node,
    NodeKind,
    entity,
    relation,
    operation,
    struct,
    list_node,
    text,
    number,
    normalize,
    fingerprint,
)

from .code_ast import build_code_ast_summary, compute_code_ast_stats
from .explain import render_explanation, render_struct_sentence
from .rules import apply_rules
from .state import ISR, SessionCtx

Handler = Callable[[ISR, Tuple[Node, ...], SessionCtx], ISR]


def apply_operator(isr: ISR, op: Node, session: SessionCtx) -> ISR:
    label = (op.label or "").upper()
    handler = _HANDLERS.get(label)
    if handler is None:
        return isr.snapshot()
    return handler(isr.snapshot(), op.args, session)


def _update(
    isr: ISR,
    *,
    relations: Tuple[Node, ...] | None = None,
    context: Tuple[Node, ...] | None = None,
    goals: Iterable[Node] | None = None,
    ops_queue: Iterable[Node] | None = None,
    answer: Node | None = None,
    quality: float | None = None,
) -> ISR:
    return ISR(
        ontology=isr.ontology,
        relations=relations if relations is not None else isr.relations,
        context=context if context is not None else isr.context,
        goals=deque(goals if goals is not None else isr.goals),
        ops_queue=deque(ops_queue if ops_queue is not None else isr.ops_queue),
        answer=answer if answer is not None else isr.answer,
        quality=quality if quality is not None else isr.quality,
    )


def _op_normalize(isr: ISR, _: Tuple[Node, ...], __: SessionCtx) -> ISR:
    normalized_relations: list[Node] = []
    seen = set()
    removed = 0
    for rel in isr.relations:
        canonical = normalize(rel)
        fingerprint_value = fingerprint(canonical)
        if fingerprint_value in seen:
            removed += 1
            continue
        seen.add(fingerprint_value)
        normalized_relations.append(canonical)
    normalized_relations.sort(key=lambda node: (node.label or "", fingerprint(node)))
    summary = struct(
        tag=entity("normalize_summary"),
        total=number(len(isr.relations)),
        deduped=number(len(normalized_relations)),
        removed=number(removed),
    )
    context = isr.context + (summary,)
    quality = min(1.0, max(isr.quality, 0.35 if removed else 0.3))
    return _update(isr, relations=tuple(normalized_relations), context=context, quality=quality)


def _op_answer(isr: ISR, args: Tuple[Node, ...], _: SessionCtx) -> ISR:
    payload = args[0] if args else struct()
    rendered = _render_struct(payload)
    answer = struct(answer=rendered)
    return _update(isr, answer=answer, quality=min(1.0, isr.quality + 0.2))


def _op_explain(isr: ISR, args: Tuple[Node, ...], _: SessionCtx) -> ISR:
    focus = args[0] if args else struct()
    report = render_explanation(isr, focus)
    answer_node = struct(answer=text(report))
    return _update(isr, answer=answer_node, quality=max(isr.quality, 0.4))


def _op_summarize(isr: ISR, _: Tuple[Node, ...], __: SessionCtx) -> ISR:
    highlights = ", ".join(rel.label or "" for rel in isr.relations[:3]) or "sem relações"
    summary_text = text(f"Resumo: {highlights}.")
    return _update(isr, answer=struct(answer=summary_text), quality=max(isr.quality, 0.5))


def _op_infer(isr: ISR, _: Tuple[Node, ...], session: SessionCtx) -> ISR:
    derived = apply_rules(isr.ontology + isr.relations, session.kb_rules)
    if not derived:
        return isr
    merged = tuple(dict.fromkeys(isr.relations + tuple(normalize(rel) for rel in derived)))
    return _update(isr, relations=merged, quality=min(1.0, isr.quality + 0.05))


def _op_compare(isr: ISR, args: Tuple[Node, ...], _: SessionCtx) -> ISR:
    if len(args) != 2:
        return isr
    a, b = args
    rel = relation("EQUAL", a, b) if a == b else relation("DIFFERENT", a, b)
    context = isr.context + (rel,)
    relations = isr.relations + (rel,)
    return _update(isr, context=context, relations=relations)


def _op_extract(isr: ISR, args: Tuple[Node, ...], _: SessionCtx) -> ISR:
    if len(args) != 2 or args[0].kind is not NodeKind.STRUCT:
        return isr
    target = args[0]
    key = args[1].label or ""
    for field, value in target.fields:
        if field == key:
            context = isr.context + (value,)
            return _update(isr, context=context)
    return isr


def _op_expand(isr: ISR, args: Tuple[Node, ...], _: SessionCtx) -> ISR:
    additions = []
    for arg in args:
        if arg.kind is NodeKind.ENTITY:
            additions.append(relation("IS_A", arg, entity("coisa")))
    if not additions:
        return isr
    relations = isr.relations + tuple(additions)
    return _update(isr, relations=relations)


def _op_map(isr: ISR, args: Tuple[Node, ...], _: SessionCtx) -> ISR:
    if not args or args[0].kind is not NodeKind.LIST:
        return isr
    source = args[0]
    op_template = args[1] if len(args) > 1 and args[1].kind is NodeKind.OP else None
    mapped_items = []
    for item in source.args:
        if op_template:
            mapped_items.append(operation(op_template.label or "MAP_ITEM", item))
        else:
            mapped_items.append(item)
    result = list_node(mapped_items)
    context = isr.context + (result,)
    return _update(isr, context=context)


def _op_reduce(isr: ISR, args: Tuple[Node, ...], _: SessionCtx) -> ISR:
    if not args or args[0].kind is not NodeKind.LIST:
        return isr
    items = args[0].args
    if all(item.kind is NodeKind.NUMBER and item.value is not None for item in items):
        value = sum(item.value for item in items if item.value is not None)
        result = number(value)
    else:
        result = struct(count=number(len(items)))
    context = isr.context + (result,)
    return _update(isr, context=context)


def _op_rewrite(isr: ISR, args: Tuple[Node, ...], _: SessionCtx) -> ISR:
    if not args:
        return isr
    target = normalize(args[0])
    context = isr.context + (target,)
    return _update(isr, context=context)


def _op_align(isr: ISR, _: Tuple[Node, ...], __: SessionCtx) -> ISR:
    relations = tuple(sorted(dict.fromkeys(isr.relations), key=lambda rel: (rel.label, len(rel.args))))
    context = tuple(dict.fromkeys(isr.context))
    return _update(isr, relations=relations, context=context)


def _op_stabilize(isr: ISR, _: Tuple[Node, ...], session: SessionCtx) -> ISR:
    target = max(session.config.min_quality, min(0.95, isr.quality + 0.1))
    return _update(isr, quality=target)


def _op_code_eval_pure(isr: ISR, args: Tuple[Node, ...], _: SessionCtx) -> ISR:
    if not args:
        return isr
    expr = args[0]
    try:
        result, descriptor = _evaluate_pure_expr(expr)
    except _PureEvalError as exc:
        error_struct = struct(eval_error=text("code/EVAL_PURE"), detail=text(str(exc)))
        context = isr.context + (error_struct,)
        return _update(isr, context=context)
    summary = struct(expr=expr, operator=text(descriptor), result=result)
    quality = min(1.0, max(isr.quality, 0.45))
    context = isr.context + (summary,)
    return _update(isr, context=context, quality=quality)


def _op_rewrite_code(isr: ISR, _: Tuple[Node, ...], __: SessionCtx) -> ISR:
    code_nodes = [node for node in isr.context if _is_code_ast(node)]
    if not code_nodes:
        return isr
    new_relations = list(isr.relations)
    new_context = list(isr.context)
    existing = {fingerprint(node) for node in new_context}
    for code_node in code_nodes:
        stats = compute_code_ast_stats(code_node)
        summary = build_code_ast_summary(code_node, stats)
        if fingerprint(summary) not in existing:
            new_context.append(summary)
            existing.add(fingerprint(summary))
        lang_entity = entity(f"code/lang::{stats.language}")
        rel = relation("code/FUNCTION_COUNT", lang_entity, number(stats.function_count))
        new_relations.append(rel)
    quality = min(1.0, max(isr.quality, 0.55))
    return _update(isr, relations=tuple(new_relations), context=tuple(new_context), quality=quality)


def _op_trace_summary(isr: ISR, args: Tuple[Node, ...], _: SessionCtx) -> ISR:
    reasoning_node = args[0] if args else None
    summary = _build_trace_summary(reasoning_node)
    if summary is None:
        return isr
    context = isr.context + (summary,)
    quality = min(1.0, max(isr.quality, 0.6))
    return _update(isr, context=context, quality=quality)


def _op_memory_recall(isr: ISR, args: Tuple[Node, ...], _: SessionCtx) -> ISR:
    if not args:
        return isr
    memory_node = args[0]
    entries_field = dict(memory_node.fields).get("entries")
    if entries_field is None or entries_field.kind is not NodeKind.LIST:
        context = isr.context + (memory_node,)
        return _update(isr, context=context, quality=isr.quality)
    new_context = list(isr.context)
    seen = {fingerprint(node) for node in new_context}
    for entry in entries_field.args:
        entry_fp = fingerprint(entry)
        if entry_fp not in seen:
            new_context.append(entry)
            seen.add(entry_fp)
    new_context.append(memory_node)
    quality = min(1.0, max(isr.quality, 0.62))
    return _update(isr, context=tuple(new_context), quality=quality)


def _op_memory_link(isr: ISR, args: Tuple[Node, ...], _: SessionCtx) -> ISR:
    if not args:
        return isr
    entry = args[0]
    if entry.kind is not NodeKind.STRUCT:
        return isr
    fields = dict(entry.fields)
    tag_node = fields.get("tag")
    if not tag_node or (tag_node.label or "").lower() != "memory_entry":
        return isr
    route_node = fields.get("route") or entity("unknown")
    preview_node = fields.get("answer_preview") or text("")
    reasoning_node = fields.get("reasoning_digest") or text("")
    expression_node = fields.get("expression_digest") or text("")
    link = struct(
        tag=entity("memory_link"),
        route=route_node,
        answer_preview=preview_node,
        reasoning_digest=reasoning_node,
        expression_digest=expression_node,
    )
    new_context = isr.context + (link,)
    reason_text = _node_text(reasoning_node)
    expr_text = _node_text(expression_node) or _node_text(preview_node)
    link_rel = relation(
        "memory/LINKS",
        entity(reason_text or "memory"),
        entity(expr_text or "memory"),
    )
    new_relations = isr.relations + (link_rel,)
    quality = min(1.0, max(isr.quality, 0.64))
    return _update(isr, relations=new_relations, context=new_context, quality=quality)


def _is_code_ast(node: Node) -> bool:
    fields = dict(node.fields)
    tag = fields.get("tag")
    return bool(tag and (tag.label or "").lower() == "code_ast")


def _render_struct(node: Node) -> Node:
    language_node = _field_node(node, "language") or _field_node(node, "plan_language")
    language = language_node.label if language_node and language_node.label else None
    return text(render_struct_sentence(node, language=language))


def _field_node(node: Node, field: str) -> Node | None:
    for key, value in node.fields:
        if key == field:
            return value
    return None


class _PureEvalError(Exception):
    """Erro determinístico durante a avaliação de uma expressão pura."""


def _evaluate_pure_expr(node: Node) -> Tuple[Node, str]:
    if node.kind in (NodeKind.NUMBER, NodeKind.TEXT, NodeKind.BOOL):
        return node, "literal"
    if node.kind is NodeKind.STRUCT:
        binop = _field_node(node, "binop")
        if binop is not None:
            return _evaluate_binop(binop)
    raise _PureEvalError(f"Unsupported expression kind '{node.kind.value}'")


def _evaluate_binop(node: Node) -> Tuple[Node, str]:
    if node.kind is not NodeKind.STRUCT:
        raise _PureEvalError("binop payload must be a STRUCT")
    op_node = _field_node(node, "op")
    left_node = _field_node(node, "left")
    right_node = _field_node(node, "right")
    if op_node is None or left_node is None or right_node is None:
        raise _PureEvalError("binop struct requires 'op', 'left' and 'right'")
    op_label = (op_node.label or "").strip()
    if not op_label:
        raise _PureEvalError("binop op label cannot be empty")
    left_result, _ = _evaluate_pure_expr(left_node)
    right_result, _ = _evaluate_pure_expr(right_node)
    result = _apply_binop(op_label, left_result, right_result)
    return result, op_label


def _apply_binop(op_label: str, left: Node, right: Node) -> Node:
    op_key = op_label.upper()
    if left.kind is NodeKind.NUMBER and right.kind is NodeKind.NUMBER:
        return number(_apply_numeric_binop(op_key, left.value, right.value))
    if op_key == "ADD" and left.kind is NodeKind.TEXT and right.kind is NodeKind.TEXT:
        return text((left.label or "") + (right.label or ""))
    if op_key == "MULT":
        if left.kind is NodeKind.TEXT and right.kind is NodeKind.NUMBER:
            return text(_repeat_text(left.label or "", right.value))
        if left.kind is NodeKind.NUMBER and right.kind is NodeKind.TEXT:
            return text(_repeat_text(right.label or "", left.value))
    raise _PureEvalError(
        f"Unsupported operands for {op_label}: {left.kind.value}, {right.kind.value}"
    )


def _apply_numeric_binop(op_key: str, left: float | None, right: float | None) -> float:
    a = _ensure_number(left)
    b = _ensure_number(right)
    if op_key == "ADD":
        return a + b
    if op_key == "SUB":
        return a - b
    if op_key == "MULT":
        return a * b
    if op_key == "DIV":
        if b == 0.0:
            raise _PureEvalError("Division by zero")
        return a / b
    if op_key == "FLOORDIV":
        if b == 0.0:
            raise _PureEvalError("Division by zero")
        return math.floor(a / b)
    if op_key == "MOD":
        if b == 0.0:
            raise _PureEvalError("Modulo by zero")
        return a % b
    if op_key == "POW":
        if abs(b) > 100:  # Prevent overflow and performance issues
            raise _PureEvalError("Exponent too large")
        return math.pow(a, b)
    raise _PureEvalError(f"Unsupported numeric operator '{op_key}'")


def _ensure_number(value: float | None) -> float:
    if value is None:
        raise _PureEvalError("Numeric operand is undefined")
    return float(value)


def _repeat_text(payload: str, multiplier: float | None) -> str:
    count = _ensure_number(multiplier)
    if not count.is_integer():
        raise _PureEvalError("String multiplier must be an integer")
    repeats = int(count)
    if repeats < 0 or repeats > 1024:
        raise _PureEvalError("String multiplier out of bounds")
    return payload * repeats


_HANDLERS: Dict[str, Handler] = {
    "NORMALIZE": _op_normalize,
    "ANSWER": _op_answer,
    "EXPLAIN": _op_explain,
    "SUMMARIZE": _op_summarize,
    "INFER": _op_infer,
    "COMPARE": _op_compare,
    "EXTRACT": _op_extract,
    "EXPAND": _op_expand,
    "MAP": _op_map,
    "REDUCE": _op_reduce,
    "REWRITE": _op_rewrite,
    "REWRITE_CODE": _op_rewrite_code,
    "ALIGN": _op_align,
    "STABILIZE": _op_stabilize,
    "CODE/EVAL_PURE": _op_code_eval_pure,
    "TRACE_SUMMARY": _op_trace_summary,
    "MEMORY_RECALL": _op_memory_recall,
    "MEMORY_LINK": _op_memory_link,
}


__all__ = ["apply_operator"]


def _node_text(node: Node | None) -> str:
    if node is None:
        return ""
    if node.label:
        return node.label
    if node.value is not None:
        return str(node.value)
    return ""


def _build_trace_summary(reasoning: Node | None) -> Node | None:
    if reasoning is None or reasoning.kind is not NodeKind.STRUCT:
        return None
    fields = dict(reasoning.fields)
    operations = fields.get("operations")
    stats_node = fields.get("operator_stats")
    digest_node = fields.get("digest")
    total_steps = 0
    unique_ops: Dict[str, int] = {}
    first_label = ""
    last_label = ""
    if operations is not None and operations.kind is NodeKind.LIST:
        total_steps = len(operations.args)
        for idx, entry in enumerate(operations.args):
            entry_fields = dict(entry.fields)
            label = (entry_fields.get("label").label if entry_fields.get("label") else "").upper()
            if not label:
                continue
            if idx == 0:
                first_label = label
            last_label = label
            unique_ops[label] = unique_ops.get(label, 0) + 1
    elif stats_node is not None and stats_node.kind is NodeKind.LIST:
        for entry in stats_node.args:
            entry_fields = dict(entry.fields)
            label = (entry_fields.get("label").label or "").upper()
            count = entry_fields.get("count").value if entry_fields.get("count") else 0
            if not label:
                continue
            unique_ops[label] = int(count or 0)
            total_steps += int(count or 0)
    dominant_op = ""
    max_count = -1
    for label, count in unique_ops.items():
        if count > max_count:
            dominant_op = label
            max_count = count
    summary_fields: Dict[str, Node] = {
        "tag": entity("trace_summary"),
        "total_steps": number(total_steps),
        "unique_ops": number(len(unique_ops)),
    }
    if first_label:
        summary_fields["first_op"] = entity(first_label)
    if last_label:
        summary_fields["last_op"] = entity(last_label)
    if dominant_op:
        summary_fields["dominant_op"] = entity(dominant_op)
    digest_label = digest_node.label if digest_node and digest_node.label else ""
    if digest_label:
        summary_fields["reasoning_digest"] = text(digest_label)
    elif reasoning is not None:
        summary_fields["reasoning_digest"] = text(fingerprint(reasoning))
    return struct(**summary_fields)
