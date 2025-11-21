"""
Funções de normalização canônica da LIU.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .arena import canonical
from .nodes import Node, NodeKind


def normalize(node: Node) -> Node:
    if node.kind is NodeKind.STRUCT:
        fields = tuple(sorted(((k, normalize(v)) for k, v in node.fields), key=lambda pair: pair[0]))
        return canonical(Node(kind=node.kind, label=node.label, args=node.args, fields=fields, value=node.value))
    if node.kind is NodeKind.LIST:
        items = tuple(normalize(arg) for arg in node.args)
        return canonical(Node(kind=node.kind, label=node.label, args=items, fields=node.fields, value=node.value))
    if node.args:
        args = tuple(normalize(arg) for arg in node.args)
        return canonical(Node(kind=node.kind, label=node.label, args=args, fields=node.fields, value=node.value))
    return canonical(node)


def dedup_relations(relations: Iterable[Node]) -> tuple[Node, ...]:
    seen = {}
    for rel in relations:
        normalized = normalize(rel)
        seen[normalized] = normalized
    return tuple(sorted(seen.values(), key=_relation_key))


def _relation_key(rel: Node) -> tuple:
    return (rel.label, tuple(arg.label for arg in rel.args))


__all__ = ["normalize", "dedup_relations"]
