"""
Operadores Φ do NSR.
"""

from __future__ import annotations

from collections import deque
from typing import Deque, Iterable, Tuple

from liu import (
    Node,
    NodeKind,
    relation,
    operation,
    struct,
    list_node,
    text,
    boolean,
    normalize,
)

from .rules import apply_rules
from .state import ISR, SessionCtx


def apply_operator(isr: ISR, op: Node, session: SessionCtx) -> ISR:
    label = op.label or ""
    if label == "NORMALIZE":
        return _op_normalize(isr)
    if label == "ANSWER":
        return _op_answer(isr, op.args[0] if op.args else struct())
    if label == "INFER":
        return _op_infer(isr, session)
    if label == "COMPARE":
        return _op_compare(isr, op.args)
    if label == "EXTRACT":
        return _op_extract(isr, op.args)
    if label == "SUMMARIZE":
        return _op_summarize(isr)
    if label == "EXPLAIN":
        return _op_explain(isr)
    if label == "EXPAND":
        return _op_expand(isr, op.args)
    return isr


def _with(
    isr: ISR,
    *,
    relations: Tuple[Node, ...] | None = None,
    context: Tuple[Node, ...] | None = None,
    answer: Node | None = None,
    quality: float | None = None,
) -> ISR:
    return ISR(
        ontology=isr.ontology,
        relations=relations if relations is not None else isr.relations,
        context=context if context is not None else isr.context,
        goals=isr.goals,
        ops_queue=isr.ops_queue,
        answer=answer if answer is not None else isr.answer,
        quality=quality if quality is not None else isr.quality,
    )


def _op_normalize(isr: ISR) -> ISR:
    normalized = tuple(normalize(rel) for rel in isr.relations)
    return _with(isr, relations=normalized)


def _op_answer(isr: ISR, payload: Node) -> ISR:
    rendered = _render_struct(payload)
    answer = struct(answer=rendered)
    return _with(isr, answer=answer, quality=min(1.0, isr.quality + 0.2))


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
    return ""


def _op_infer(isr: ISR, session: SessionCtx) -> ISR:
    derived = apply_rules(isr.ontology + isr.relations, session.kb_rules)
    if not derived:
        return isr
    merged = tuple(dict.fromkeys(isr.relations + tuple(derived)))
    return _with(isr, relations=merged)


def _op_compare(isr: ISR, args: Tuple[Node, ...]) -> ISR:
    if len(args) != 2:
        return isr
    a, b = args
    if a == b:
        rel = relation("EQUAL", a, b)
    else:
        rel = relation("DIFFERENT", a, b)
    context = isr.context + (rel,)
    relations = isr.relations + (rel,)
    return _with(isr, context=context, relations=relations)


def _op_extract(isr: ISR, args: Tuple[Node, ...]) -> ISR:
    if len(args) != 2 or args[0].kind is not NodeKind.STRUCT:
        return isr
    target = args[0]
    key = args[1].label or ""
    for field, value in target.fields:
        if field == key:
            context = isr.context + (value,)
            return _with(isr, context=context)
    return isr


def _op_expand(isr: ISR, args: Tuple[Node, ...]) -> ISR:
    additions = []
    for arg in args:
        if arg.kind is NodeKind.ENTITY:
            additions.append(relation("IS_A", arg, entity("coisa")))
    if not additions:
        return isr
    relations = isr.relations + tuple(additions)
    return _with(isr, relations=relations)


def _op_summarize(isr: ISR) -> ISR:
    highlights = ", ".join(rel.label or "" for rel in isr.relations[:3])
    summary_text = text(f"Resumo: {highlights or 'sem relações'}.")
    return _with(isr, answer=struct(answer=summary_text), quality=max(isr.quality, 0.5))


def _op_explain(isr: ISR) -> ISR:
    explanation = text(f"Explicação: {len(isr.relations)} relações, qualidade {isr.quality:.2f}.")
    return _with(isr, answer=struct(answer=explanation), quality=isr.quality)


__all__ = ["apply_operator"]
