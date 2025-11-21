"""
Definições de enums básicas para a LIU: NodeKind e Sort.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import Tuple


class NodeKind(str, Enum):
    ENTITY = "ENTITY"
    REL = "REL"
    OP = "OP"
    STRUCT = "STRUCT"
    LIST = "LIST"
    TEXT = "TEXT"
    NUMBER = "NUMBER"
    BOOL = "BOOL"
    VAR = "VAR"
    NIL = "NIL"


class Sort(str, Enum):
    THING = "Thing"
    TYPE = "Type"
    PROP = "Prop"
    RELATION = "Relation"
    OPERATOR = "Operator"
    STATE = "State"
    CONTEXT = "Context"
    GOAL = "Goal"
    ANSWER = "Answer"
    TEXT = "Text"
    NUMBER = "Number"
    BOOL = "Bool"
    LIST = "List"
    ANY = "Any"


@dataclass(frozen=True, slots=True)
class Signature:
    name: str
    args: Tuple[Sort, ...]
    returns: Sort


__all__ = ["NodeKind", "Sort", "Signature"]
