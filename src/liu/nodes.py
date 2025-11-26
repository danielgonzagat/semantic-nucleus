"""
Estruturas imutáveis para nós LIU.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Tuple

from .atoms import atom
from .kinds import NodeKind


FieldsTuple = Tuple[Tuple[str, "Node"], ...]


@dataclass(frozen=True)
class Node:
    kind: NodeKind
    label: str | None = None
    args: Tuple["Node", ...] = ()
    fields: FieldsTuple = ()
    value: object | None = None

    def with_args(self, args: Iterable["Node"]) -> "Node":
        return Node(kind=self.kind, label=self.label, args=tuple(args), fields=self.fields, value=self.value)

    def with_fields(self, items: Iterable[Tuple[str, "Node"]]) -> "Node":
        ordered = tuple(sorted(((atom(k), v) for k, v in items), key=lambda pair: pair[0]))
        return Node(kind=self.kind, label=self.label, args=self.args, fields=ordered, value=self.value)

    def is_nil(self) -> bool:
        return self.kind is NodeKind.NIL

    def __str__(self) -> str:
        return f"{self.kind.value}({self.label or ''})"


NIL = Node(kind=NodeKind.NIL)


def entity(name: str) -> Node:
    return Node(kind=NodeKind.ENTITY, label=atom(name))


def relation(name: str, *args: Node) -> Node:
    return Node(kind=NodeKind.REL, label=atom(name), args=tuple(args))


def operation(name: str, *args: Node) -> Node:
    return Node(kind=NodeKind.OP, label=atom(name), args=tuple(args))


def struct(**fields: Node) -> Node:
    return Node(kind=NodeKind.STRUCT).with_fields(fields.items())


def list_node(items: Iterable[Node]) -> Node:
    return Node(kind=NodeKind.LIST, args=tuple(items))


def text(value: str) -> Node:
    return Node(kind=NodeKind.TEXT, label=value)


def number(value: float | int) -> Node:
    return Node(kind=NodeKind.NUMBER, value=float(value))


def boolean(value: bool) -> Node:
    return Node(kind=NodeKind.BOOL, value=bool(value))


def var(name: str) -> Node:
    if not name.startswith("?"):
        raise ValueError("Variable names must start with '?'")
    return Node(kind=NodeKind.VAR, label=atom(name))


__all__ = [
    "Node",
    "NodeKind",
    "FieldsTuple",
    "entity",
    "relation",
    "operation",
    "struct",
    "list_node",
    "text",
    "number",
    "boolean",
    "var",
    "NIL",
]
