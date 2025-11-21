"""
Validação de bem-formação e tipagem simples para LIU.
"""

from __future__ import annotations

from typing import Dict, Tuple

from .kinds import NodeKind, Sort
from .nodes import Node
from .signatures import OP_SIGNATURES, REL_SIGNATURES


class LIUError(Exception):
    """Erro de bem-formação."""


FIELD_SIGNATURES: Dict[str, Sort] = {
    "subject": Sort.THING,
    "action": Sort.ANY,
    "object": Sort.THING,
    "context": Sort.CONTEXT,
    "modifier": Sort.LIST,
    "goal": Sort.GOAL,
    "state": Sort.STATE,
    "answer": Sort.TEXT,
    "params": Sort.LIST,
    "body": Sort.LIST,
    "ret": Sort.TYPE,
    "name": Sort.ANY,
    "clauses": Sort.LIST,
    "guard": Sort.ANY,
    "pattern": Sort.ANY,
    "args": Sort.LIST,
    "assign": Sort.STRUCTURE,
    "target": Sort.ANY,
    "value": Sort.ANY,
    "return_": Sort.ANY,
    "binop": Sort.STRUCTURE,
    "metadata": Sort.CONTEXT,
}


def infer_sort(node: Node) -> Sort:
    match node.kind:
        case NodeKind.ENTITY:
            return Sort.THING
        case NodeKind.TEXT:
            return Sort.TEXT
        case NodeKind.NUMBER:
            return Sort.NUMBER
        case NodeKind.BOOL:
            return Sort.BOOL
        case NodeKind.LIST:
            return Sort.LIST
        case NodeKind.STRUCT:
            return Sort.STATE
        case NodeKind.REL:
            return Sort.PROP
        case NodeKind.OP:
            return Sort.OPERATOR
        case NodeKind.VAR:
            return Sort.ANY
        case NodeKind.NIL:
            return Sort.ANY
        case _:
            raise LIUError(f"Unknown node kind {node.kind}")


def check(node: Node) -> None:
    """Dispara LIUError caso o nó viole a gramática."""

    _check(node, path=())


def _check(node: Node, path: Tuple[str, ...]) -> Sort:
    kind = node.kind
    if kind is NodeKind.REL:
        sig = REL_SIGNATURES.get(node.label or "")
        if sig is None:
            raise LIUError(f"Unknown relation {node.label}")
        if len(node.args) != len(sig.args):
            raise LIUError(f"Arity mismatch for {node.label}")
        for arg, expected in zip(node.args, sig.args):
            got = _check(arg, path + (node.label or "",))
            _ensure_sort(arg, got, expected, node.label)
        return sig.returns

    if kind is NodeKind.OP:
        sig = OP_SIGNATURES.get(node.label or "")
        if sig is None:
            raise LIUError(f"Unknown operator {node.label}")
        if len(node.args) != len(sig.args):
            raise LIUError(f"Arity mismatch for operator {node.label}")
        for arg, expected in zip(node.args, sig.args):
            got = _check(arg, path + (node.label or "",))
            _ensure_sort(arg, got, expected, node.label)
        return sig.returns

    if kind is NodeKind.STRUCT:
        seen = []
        for key, value in node.fields:
            if key in seen:
                raise LIUError(f"Duplicate struct field {key}")
            seen.append(key)
            expected = FIELD_SIGNATURES.get(key, Sort.ANY)
            got = _check(value, path + (key,))
            _ensure_sort(value, got, expected, key)
        if seen != sorted(seen):
            raise LIUError("Struct fields must be sorted lexicographically")
        return Sort.STATE

    if kind is NodeKind.LIST:
        for item in node.args:
            _check(item, path + ("list",))
        return Sort.LIST

    if kind is NodeKind.NIL:
        return Sort.ANY

    got = infer_sort(node)
    return got


def _ensure_sort(node: Node, got: Sort, expected: Sort, label: str | None) -> None:
    if expected is Sort.ANY:
        return
    if got is Sort.ANY or got == expected:
        return
    raise LIUError(f"Sort mismatch for {label}: expected {expected}, got {got}")


__all__ = ["check", "LIUError", "FIELD_SIGNATURES"]
