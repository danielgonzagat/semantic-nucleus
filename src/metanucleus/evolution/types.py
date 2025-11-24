"""
Tipos utilitários para patches de autoevolução.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import shutil
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
        application = apply_unified_diff(root, self.diff)
        for rel_path, content in application.updated_files.items():
            target = root / rel_path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
        for rel_path in application.deleted_files:
            target = root / rel_path
            if target.is_dir():
                shutil.rmtree(target, ignore_errors=True)
            elif target.exists():
                target.unlink()
        touched = set(application.updated_files.keys())
        touched.update(application.deleted_files)
        return sorted(touched)

    @property
    def type(self) -> str:  # compatibilidade com código legado
        return self.domain


__all__ = ["EvolutionPatch"]
