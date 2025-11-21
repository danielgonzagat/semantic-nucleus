"""
Operadores Φ do NSR.
"""

from __future__ import annotations

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


def _render_struct(node: Node) -> Node:
    subject = _field_label(node, "subject")
    action = _field_label(node, "action")
    obj = _field_label(node, "object")
    modifier = _field_label(node, "modifier")
    pieces = [subject, action]
    if obj:
        pieces.append(obj)
    if modifier:
        pieces.append(modifier)
    sent = " ".join(filter(None, pieces)).strip()
    if not sent:
        sent = "Resposta não determinada"
    else:
        sent = sent[0].upper() + sent[1:] + "."
    return text(sent)


def _field_label(node: Node, field: str) -> str:
    for key, value in node.fields:
        if key == field:
            if value.kind is NodeKind.ENTITY:
                return value.label or ""
            if value.kind is NodeKind.LIST:
                return " ".join(item.label or "" for item in value.args if item.label)
            if value.kind is NodeKind.TEXT:
                return value.label or ""
    return ""


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
}


__all__ = ["apply_operator"]
