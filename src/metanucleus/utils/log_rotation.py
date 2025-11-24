"""
Utilitário simples para limitar o tamanho de arquivos JSONL usados pelos logs.
"""

from __future__ import annotations

from collections import deque
from pathlib import Path


def enforce_log_limit(path: Path, max_lines: int) -> None:
    """
    Mantém apenas as últimas `max_lines` linhas do arquivo JSONL.

    Útil para impedir que logs cresçam indefinidamente. Quando o arquivo ainda
    não atingiu o limite, nada é regravado.
    """

    if max_lines <= 0 or not path.exists():
        return

    buffer: deque[str] = deque()
    total = 0
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            total += 1
            buffer.append(line)
            if len(buffer) > max_lines:
                buffer.popleft()

    if total <= max_lines:
        return

    with path.open("w", encoding="utf-8") as handle:
        handle.writelines(buffer)


__all__ = ["enforce_log_limit"]
