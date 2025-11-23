"""
Helpers determinísticos para localizar o diretório raiz do projeto.
"""

from __future__ import annotations

from pathlib import Path


def get_project_root(start: Path | None = None) -> Path:
    """
    Retorna o diretório raiz do repositório, identificado pela presença
    de um `pyproject.toml`. Caso não encontre, devolve o directório pai
    imediato do caminho informado.
    """

    current = (start or Path(__file__)).resolve()
    for candidate in [current, *current.parents]:
        if (candidate / "pyproject.toml").exists():
            return candidate
    return current.parents[-1]
