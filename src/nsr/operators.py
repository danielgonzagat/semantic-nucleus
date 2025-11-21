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
)

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
    normalized = tuple(normalize(rel) for rel in isr.relations)
    return _update(isr, relations=normalized, quality=min(1.0, max(isr.quality, 0.3)))


def _op_answer(isr: ISR, args: Tuple[Node, ...], _: SessionCtx) -> ISR:
    payload = args[0] if args else struct()
    rendered = _render_struct(payload)
    answer = struct(answer=rendered)
    return _update(isr, answer=answer, quality=min(1.0, isr.quality + 0.2))


def _op_explain(isr: ISR, args: Tuple[Node, ...], _: SessionCtx) -> ISR:
    focus = args[0] if args else struct()
    explanation = text(
        f"Explicação: {len(isr.relations)} relações, contexto {len(isr.context)}, foco={focus.kind.value}."
    )
    return _update(isr, answer=struct(answer=explanation))


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


def _render_struct(node: Node) -> Node:
    subject = _field_label(node, "subject")
    action = _field_label(node, "action")
    obj = _field_label(node, "object")
    modifier = _field_label(node, "modifier")
    relations_summary = _format_relations(_field_node(node, "relations"))
    pieces = [subject, action]
    if obj:
        pieces.append(obj)
    if modifier:
        pieces.append(modifier)
    sent = " ".join(filter(None, pieces)).strip()
    clauses = []
    if not sent:
        clauses.append("Resposta não determinada")
    else:
        clauses.append(sent[0].upper() + sent[1:])
    if relations_summary:
        clauses.append(f"Relações: {relations_summary}")
    final = ". ".join(clauses) + "."
    return text(final)


def _field_label(node: Node, field: str) -> str:
    target = _field_node(node, field)
    if target is None:
        return ""
    if target.kind is NodeKind.ENTITY:
        return target.label or ""
    if target.kind is NodeKind.LIST:
        return " ".join(item.label or "" for item in target.args if item.label)
    if target.kind is NodeKind.TEXT:
        return target.label or ""
    return ""


def _field_node(node: Node, field: str) -> Node | None:
    for key, value in node.fields:
        if key == field:
            return value
    return None


def _format_relations(relations_node: Node | None) -> str | None:
    if relations_node is None or relations_node.kind is not NodeKind.LIST:
        return None
    phrases = []
    for candidate in relations_node.args:
        phrase = _render_relation(candidate)
        if phrase:
            phrases.append(phrase)
    if not phrases:
        return None
    return "; ".join(phrases)


def _render_relation(node: Node) -> str | None:
    if node.kind is not NodeKind.REL or not node.label:
        return None
    if len(node.args) < 2:
        return None
    source = _node_token(node.args[0])
    target = _node_token(node.args[1])
    if not source or not target:
        return None
    rel_label = node.label.replace("_", " ").lower()
    return f"{source} {rel_label} {target}"


def _node_token(node: Node) -> str:
    if node.kind in (NodeKind.ENTITY, NodeKind.TEXT):
        return (node.label or "").strip()
    return ""


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
    "ALIGN": _op_align,
    "STABILIZE": _op_stabilize,
    "CODE/EVAL_PURE": _op_code_eval_pure,
}


__all__ = ["apply_operator"]
