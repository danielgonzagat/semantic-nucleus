"""
Parser Semântico Estrutural (PSE).
"""

from __future__ import annotations

from typing import List

from liu import Node, entity, relation, struct, list_node

from .state import Token


def build_struct(tokens: List[Token]) -> Node:
    subject = None
    action = None
    obj = None
    modifiers = []
    relations: List[Node] = []
    for idx, token in enumerate(tokens):
        if token.tag == "ACTION" and action is None:
            action = entity(token.lemma)
            subject = subject or _find_entity(tokens, idx, reverse=True)
            obj = obj or _find_entity(tokens, idx, reverse=False)
        elif token.tag == "QUALIFIER":
            modifiers.append(entity(token.lemma))
        elif token.tag == "RELWORD":
            rel_node = _build_relation(tokens, idx, token.payload)
            if rel_node is not None:
                relations.append(rel_node)
        elif token.tag == "ENTITY" and subject is None:
            subject = entity(token.lemma)
    fields = {}
    if subject is not None:
        fields["subject"] = subject
    if action is not None:
        fields["action"] = action
    if obj is not None:
        fields["object"] = obj
    if modifiers:
        fields["modifier"] = list_node(modifiers)
    if relations:
        fields["relations"] = list_node(relations)
    return struct(**fields)


def _find_entity(tokens: List[Token], pivot: int, reverse: bool) -> Node | None:
    positions = range(pivot - 1, -1, -1) if reverse else range(pivot + 1, len(tokens))
    for idx in positions:
        token = tokens[idx]
        if token.tag == "ENTITY":
            return entity(token.lemma)
    return None


def _build_relation(tokens: List[Token], pivot: int, rel_label: str | None) -> Node | None:
    if not rel_label:
        return None
    source = _find_entity(tokens, pivot, reverse=True)
    target = _find_entity(tokens, pivot, reverse=False)
    if source is None or target is None:
        return None
    return relation(rel_label, source, target)


__all__ = ["build_struct"]
