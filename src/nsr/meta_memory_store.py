"""
Persistência determinística da Meta-Memória.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

from liu import Node, to_json, from_json


def append_memory(path: str, memory_node: Node) -> None:
    """
    Acrescenta um `meta_memory` serializado em JSONL.
    """

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = to_json(memory_node)
    with target.open("a", encoding="utf-8") as handle:
        handle.write(payload)
        handle.write("\n")


def load_recent_memory(path: str, limit: int) -> tuple[Node, ...]:
    """
    Lê até `limit` entradas de memória em ordem cronológica.
    """

    if limit <= 0:
        return tuple()
    target = Path(path)
    if not target.exists():
        return tuple()
    with target.open("r", encoding="utf-8") as handle:
        lines = [line.strip() for line in handle.readlines() if line.strip()]
    recent = lines[-limit:]
    nodes = []
    for line in recent:
        try:
            nodes.append(from_json(line))
        except ValueError:
            continue
    return tuple(nodes)


__all__ = ["append_memory", "load_recent_memory"]
