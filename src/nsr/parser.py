"""
Parser Semântico Estrutural (PSE).
"""

from __future__ import annotations

from typing import List

from liu import Node, entity, struct, list_node

from .state import Token


def build_struct(tokens: List[Token]) -> Node:
    subject = None
    action = None
    obj = None
    modifiers = []
    for idx, token in enumerate(tokens):
        if token.tag == "ACTION" and action is None:
            action = entity(token.lemma)
            subject = subject or _find_entity(tokens, idx, reverse=True)
            obj = obj or _find_entity(tokens, idx, reverse=False)
        elif token.tag == "QUALIFIER":
            modifiers.append(entity(token.lemma))
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
    return struct(**fields)


def _find_entity(tokens: List[Token], pivot: int, reverse: bool) -> Node | None:
    positions = range(pivot - 1, -1, -1) if reverse else range(pivot + 1, len(tokens))
    for idx in positions:
        token = tokens[idx]
        if token.tag == "ENTITY":
            return entity(token.lemma)
    return None


__all__ = ["build_struct"]
