"""
liu.atoms
~~~~~~~~~

Internador determinístico de símbolos (átomos) para a Linguagem Interna
Universal (LIU). A especificação exige comparação O(1) de labels e nomes
de relações/operações; para isso, mantemos uma tabela de interning
imutável durante a execução do processo.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from threading import RLock
from typing import Dict


@dataclass()
class AtomTable:
    """Tabela global de átomos internados."""

    _forward: Dict[str, str] = field(default_factory=dict)
    _lock: RLock = field(default_factory=RLock)

    def intern(self, value: str) -> str:
        """Retorna a instância canônica de *value*."""
        if not isinstance(value, str):
            raise TypeError("atom() accepts only str")
        key = value.strip()
        if not key:
            raise ValueError("atom() cannot intern empty strings")
        with self._lock:
            cached = self._forward.get(key)
            if cached is None:
                self._forward[key] = key
                cached = key
        return cached


_ATOM_TABLE = AtomTable()


def atom(value: str) -> str:
    """Interna *value* e devolve a referência canônica."""

    return _ATOM_TABLE.intern(value)


__all__ = ["atom", "AtomTable"]
