"""
Construtores determinísticos de probabilidades contextuais (contagens LIU normalizadas).
"""

from __future__ import annotations

from collections import Counter
from typing import Iterable

from liu import Node, NodeKind, entity, list_node, number, struct as liu_struct

from .state import ISR


def build_context_probabilities(isr: ISR) -> Node:
    relation_counts = _count_labels(node.label or "" for node in isr.relations)
    context_counts = _count_labels(_node_tag(node) for node in isr.context)
    goal_counts = _count_labels(node.label or "" for node in isr.goals)
    relation_nodes = [
        liu_struct(
            tag=entity("relation_probability"),
            label=entity(label or "UNKNOWN"),
            count=number(count),
            probability=number(probability),
        )
        for label, (count, probability) in relation_counts.items()
    ]
    context_nodes = [
        liu_struct(
            tag=entity("context_probability"),
            label=entity(label or "UNKNOWN"),
            count=number(count),
            probability=number(probability),
        )
        for label, (count, probability) in context_counts.items()
    ]
    goal_nodes = [
        liu_struct(
            tag=entity("goal_probability"),
            label=entity(label or "UNKNOWN"),
            count=number(count),
            probability=number(probability),
        )
        for label, (count, probability) in goal_counts.items()
    ]
    return liu_struct(
        tag=entity("context_probabilities"),
        relation_total=number(sum(count for count, _ in relation_counts.values())),
        context_total=number(sum(count for count, _ in context_counts.values())),
        goal_total=number(sum(count for count, _ in goal_counts.values())),
        relations=list_node(relation_nodes),
        contexts=list_node(context_nodes),
        goals=list_node(goal_nodes),
    )


def _count_labels(labels: Iterable[str]) -> dict[str, tuple[int, float]]:
    counter = Counter(label for label in labels if label)
    total = sum(counter.values())
    if total == 0:
        return {}
    return {label: (count, round(count / total, 6)) for label, count in sorted(counter.items())}


def _node_tag(node: Node) -> str:
    if node.kind is not NodeKind.STRUCT:
        return (node.label or "").upper()
    tag_field = dict(node.fields).get("tag")
    return (tag_field.label or "").upper() if tag_field else (node.label or "").upper()


__all__ = ["build_context_probabilities"]
