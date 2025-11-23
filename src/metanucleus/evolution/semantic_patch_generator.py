"""
Gera sugestões de patch para semântica com base nos SemanticMismatch logs.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

from metanucleus.evolution.diff_utils import make_unified_diff
from metanucleus.evolution.semantic_mismatch_log import (
    SemanticMismatch,
    load_semantic_mismatches,
)
from metanucleus.utils.project import get_project_root


@dataclass(slots=True)
class SemanticPatchCandidate:
    title: str
    description: str
    diff: str


class SemanticPatchGenerator:
    """
    Consolida inconsistências semânticas em um arquivo Markdown de sugestões.
    """

    def __init__(
        self,
        project_root: Path | None = None,
        suggestions_path: Path | None = None,
        log_limit: int | None = None,
    ) -> None:
        self.project_root = project_root or get_project_root(Path(__file__))
        default_path = self.project_root / "src" / "metanucleus" / "data" / "semantic_suggestions.md"
        self.suggestions_path = suggestions_path or default_path
        self.log_limit = log_limit

    def generate_patches(self, max_groups: int = 20) -> List[SemanticPatchCandidate]:
        mismatches = load_semantic_mismatches(limit=self.log_limit)
        if not mismatches:
            return []
        grouped = self._group(mismatches)
        if not grouped:
            return []

        old_text = self._read_current()
        new_text = self._render(grouped[:max_groups])
        if old_text == new_text:
            return []

        diff = make_unified_diff(
            filename=str(self.suggestions_path.relative_to(self.project_root)),
            original=old_text,
            patched=new_text,
        )
        candidate = SemanticPatchCandidate(
            title=f"Auto-evolution: {len(grouped[:max_groups])} sugestões semânticas",
            description="Sugestões agregadas a partir de SemanticMismatch recentes.",
            diff=diff,
        )
        return [candidate]

    def _group(self, mismatches: List[SemanticMismatch]) -> List[Tuple[str, List[SemanticMismatch]]]:
        buckets: Dict[str, List[SemanticMismatch]] = {}
        for mismatch in mismatches:
            key = mismatch.lang or "unknown"
            buckets.setdefault(key, []).append(mismatch)
        return sorted(buckets.items(), key=lambda item: item[0])

    def _read_current(self) -> str:
        if not self.suggestions_path.exists():
            return "# Semantic Suggestions\n\n"
        return self.suggestions_path.read_text(encoding="utf-8")

    def _render(self, grouped: List[Tuple[str, List[SemanticMismatch]]]) -> str:
        lines = ["# Semantic Suggestions", ""]
        for lang, entries in grouped:
            lines.append(f"## {lang}")
            for entry in entries:
                lines.append(f"- **Frase:** {entry.phrase}")
                lines.append(f"  - Issue: {entry.issue}")
                lines.append(f"  - Esperado: `{entry.expected_repr}`")
                lines.append(f"  - Obtido: `{entry.actual_repr}`")
                if entry.file_path:
                    lines.append(f"  - Arquivo: `{entry.file_path}`")
                lines.append("")
        rendered = "\n".join(lines).rstrip() + "\n"
        return rendered


__all__ = ["SemanticPatchGenerator", "SemanticPatchCandidate"]
