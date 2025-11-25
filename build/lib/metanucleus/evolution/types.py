"""
Tipos utilitários para patches de autoevolução.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List

from metanucleus.utils.diff_apply import apply_unified_diff
from metanucleus.utils.project import get_project_root


@dataclass(slots=True)
class EvolutionPatch:
    """
    Representa um patch simbólico sugerido por algum domínio de evolução.
    """

    domain: str
    title: str
    description: str
    diff: str
    meta: Dict[str, Any] = field(default_factory=dict)

    def apply(self, repo_root: Path | None = None) -> List[str]:
        """
        Aplica o diff no disco e devolve a lista de arquivos modificados.
        """
        root = repo_root or get_project_root(Path(__file__))
        result = apply_unified_diff(root, self.diff)
        return result.touched_files

    @property
    def type(self) -> str:  # compatibilidade com código legado
        return self.domain


__all__ = ["EvolutionPatch"]
