"""
Gera sugestões de patch para regras/ontologias com base nos RuleMismatch logs.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

from metanucleus.evolution.diff_utils import make_unified_diff
from metanucleus.evolution.rule_mismatch_log import RuleMismatch, load_rule_mismatches
from metanucleus.utils.project import get_project_root


@dataclass()
class RulePatchCandidate:
    title: str
    description: str
    diff: str


class RulePatchGenerator:
    """
    Consolida os mismatches de regra em um arquivo Markdown com sugestões.
    """

    def __init__(
        self,
        project_root: Path | None = None,
        suggestions_path: Path | None = None,
        log_limit: int | None = None,
    ) -> None:
        self.project_root = project_root or get_project_root(Path(__file__))
        default_path = self.project_root / "src" / "metanucleus" / "data" / "rule_suggestions.md"
        self.suggestions_path = suggestions_path or default_path
        self.log_limit = log_limit

    def generate_patches(self, max_rules: int = 20) -> List[RulePatchCandidate]:
        mismatches = load_rule_mismatches(limit=self.log_limit)
        if not mismatches:
            return []

        grouped = self._group(mismatches)
        if not grouped:
            return []

        old_text = self._read_current()
        new_text = self._render(grouped[:max_rules])
        if old_text == new_text:
            return []

        diff = make_unified_diff(
            filename=str(self.suggestions_path.relative_to(self.project_root)),
            original=old_text,
            patched=new_text,
        )
        candidate = RulePatchCandidate(
            title=f"Auto-evolution: {len(grouped[:max_rules])} sugestões de regras",
            description="Sugestões agregadas a partir de RuleMismatch recentes.",
            diff=diff,
        )
        return [candidate]

    def _group(self, mismatches: List[RuleMismatch]) -> List[Tuple[str, List[RuleMismatch]]]:
        buckets: Dict[str, List[RuleMismatch]] = {}
        for mismatch in mismatches:
            key = mismatch.rule_name or "unknown_rule"
            buckets.setdefault(key, []).append(mismatch)
        return sorted(buckets.items(), key=lambda item: item[0])

    def _read_current(self) -> str:
        if not self.suggestions_path.exists():
            return "# Rule Suggestions\n\n"
        return self.suggestions_path.read_text(encoding="utf-8")

    def _render(self, grouped: List[Tuple[str, List[RuleMismatch]]]) -> str:
        lines = ["# Rule Suggestions", ""]
        for rule_name, entries in grouped:
            lines.append(f"## {rule_name}")
            for entry in entries:
                lines.append(f"- **Descrição:** {entry.description}")
                lines.append(f"  - Contexto: {entry.context}")
                lines.append(f"  - Esperado: `{entry.expected}`")
                lines.append(f"  - Obtido: `{entry.got}`")
                if entry.file_path:
                    lines.append(f"  - Arquivo: `{entry.file_path}`")
                lines.append("")
        rendered = "\n".join(lines).rstrip() + "\n"
        return rendered


__all__ = ["RulePatchGenerator", "RulePatchCandidate"]
