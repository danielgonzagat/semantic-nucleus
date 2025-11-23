"""
Arena imutável de nós LIU para deduplicação e auditoria.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict

from .nodes import Node


@dataclass(slots=True)
class Arena:
    """Mantém referências únicas para cada nó."""

    _cache: Dict[Node, Node] = field(default_factory=dict)

    def intern(self, node: Node) -> Node:
        cached = self._cache.get(node)
        if cached is None:
            self._cache[node] = node
            cached = node
        return cached


GLOBAL_ARENA = Arena()


def canonical(node: Node) -> Node:
    return GLOBAL_ARENA.intern(node)


__all__ = ["Arena", "canonical", "GLOBAL_ARENA"]
