"""
Tipos LIU (Linguagem Interna Universal) mínimos usados pelo Metanúcleo.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Optional


class NodeKind(Enum):
    ENTITY = auto()
    REL = auto()
    OP = auto()
    STRUCT = auto()
    LIST = auto()
    TEXT = auto()
    NUMBER = auto()
    BOOL = auto()
    NIL = auto()


@dataclass(slots=True)
class Node:
    kind: NodeKind
    label: Optional[str] = None
    args: List["Node"] = field(default_factory=list)
    fields: Dict[str, "Node"] = field(default_factory=dict)
    value_num: Optional[float] = None
    value_bool: Optional[bool] = None

    def __repr__(self) -> str:
        return f"Node(kind={self.kind.name}, label={self.label!r})"


def nil() -> Node:
    return Node(kind=NodeKind.NIL)


def entity(name: str) -> Node:
    return Node(kind=NodeKind.ENTITY, label=name)


def text(value: str) -> Node:
    return Node(kind=NodeKind.TEXT, label=value)


def number(value: float) -> Node:
    return Node(kind=NodeKind.NUMBER, value_num=float(value))


def boolean(value: bool) -> Node:
    return Node(kind=NodeKind.BOOL, value_bool=bool(value))


def struct(**fields: Node) -> Node:
    return Node(kind=NodeKind.STRUCT, fields=dict(fields))


def list_node(*items: Node) -> Node:
    return Node(kind=NodeKind.LIST, args=list(items))


def op(name: str, *args: Node) -> Node:
    return Node(kind=NodeKind.OP, label=name, args=list(args))


def rel(name: str, *args: Node) -> Node:
    return Node(kind=NodeKind.REL, label=name, args=list(args))
