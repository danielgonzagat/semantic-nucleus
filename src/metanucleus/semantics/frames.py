"""
Estruturas simples para frames semânticos usados em testes/logs.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass()
class Role:
    value: str


@dataclass()
class RoleAssignment:
    role: Role
    text: str


@dataclass()
class SemanticFrame:
    predicate: str
    roles: List[RoleAssignment]


def make_frame(predicate: str, role_map: dict[str, str]) -> SemanticFrame:
    return SemanticFrame(
        predicate=predicate,
        roles=[RoleAssignment(role=Role(name), text=text) for name, text in role_map.items()],
    )


__all__ = ["SemanticFrame", "Role", "RoleAssignment", "make_frame"]
