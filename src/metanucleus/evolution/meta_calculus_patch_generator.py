"""
Gera patches para `meta_calculus_rules.json` a partir dos mismatches registrados.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from metanucleus.evolution.diff_utils import make_unified_diff
from metanucleus.evolution.meta_calculus_mismatch_log import (
    META_CALCULUS_MISMATCH_LOG_PATH,
    MetaCalculusMismatchEntry,
    load_meta_calculus_mismatches,
)
from metanucleus.utils.project import get_project_root


@dataclass(slots=True)
class MetaCalculusPatchCandidate:
    title: str
    description: str
    diff: str


class MetaCalculusPatchGenerator:
    """
    Consolida mismatches em regras de equivalência determinísticas.
    """

    def __init__(
        self,
        project_root: Optional[Path] = None,
        rules_path: Optional[Path] = None,
        log_path: Optional[Path] = None,
        log_limit: Optional[int] = None,
    ) -> None:
        self.project_root = project_root or get_project_root(Path(__file__))
        self.rules_path = rules_path or (
            self.project_root / "src" / "metanucleus" / "data" / "meta_calculus_rules.json"
        )
        self.log_path = log_path or META_CALCULUS_MISMATCH_LOG_PATH
        self.log_limit = log_limit

    def generate_patches(self, max_new_rules: int = 10) -> List[MetaCalculusPatchCandidate]:
        mismatches = load_meta_calculus_mismatches(path=self.log_path, limit=self.log_limit)
        if not mismatches:
            return []

        rules_data = self._load_rules()
        existing_signatures = {self._signature(rule) for rule in rules_data}
        grouped = self._group_mismatches(mismatches)

        new_rules: List[Dict] = []
        for (expr, expected_repr), entries in grouped:
            if len(new_rules) >= max_new_rules:
                break
            signature = (expr.strip(), expected_repr.strip())
            if signature in existing_signatures:
                continue
            new_rule = {
                "id": f"auto_{self._hash(expr, expected_repr)}",
                "kind": "equivalence",
                "expr": expr,
                "target_repr": expected_repr,
                "enabled": True,
                "weight": 1.0,
                "examples": [
                    {
                        "test_id": e.test_id,
                        "actual_repr": e.actual_repr,
                        "error_type": e.error_type,
                    }
                    for e in entries[:3]
                ],
            }
            new_rules.append(new_rule)
            existing_signatures.add(signature)

        if not new_rules:
            return []

        original_text = (
            self.rules_path.read_text(encoding="utf-8")
            if self.rules_path.exists()
            else json.dumps({"rules": []}, ensure_ascii=False, indent=2)
        )
        patched_dataset = {"rules": rules_data + new_rules}
        patched_text = json.dumps(patched_dataset, ensure_ascii=False, indent=2, sort_keys=True)

        diff = make_unified_diff(
            filename=str(self.rules_path.relative_to(self.project_root)),
            original=original_text,
            patched=patched_text,
        )
        description_lines = [
            "Regras adicionadas automaticamente a partir de mismatches:",
        ]
        for (expr, expected_repr), entries in grouped[: len(new_rules)]:
            description_lines.append(f"- `{expr}` ⇒ `{expected_repr}` ({len(entries)} ocorrências)")

        candidate = MetaCalculusPatchCandidate(
            title=f"Auto-evolution: +{len(new_rules)} regras de meta-cálculo",
            description="\n".join(description_lines),
            diff=diff,
        )
        return [candidate]

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _load_rules(self) -> List[Dict]:
        if not self.rules_path.exists():
            return []
        data = json.loads(self.rules_path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return list(data.get("rules", []))
        if isinstance(data, list):
            return data
        return []

    def _group_mismatches(
        self,
        mismatches: List[MetaCalculusMismatchEntry],
    ) -> List[Tuple[Tuple[str, str], List[MetaCalculusMismatchEntry]]]:
        buckets: Dict[Tuple[str, str], List[MetaCalculusMismatchEntry]] = {}
        for entry in mismatches:
            key = (entry.expr.strip(), entry.expected_repr.strip())
            buckets.setdefault(key, []).append(entry)
        return sorted(buckets.items(), key=lambda item: len(item[1]), reverse=True)

    def _signature(self, rule: Dict) -> Tuple[str, str]:
        return (str(rule.get("expr", "")).strip(), str(rule.get("target_repr", "")).strip())

    def _hash(self, expr: str, expected_repr: str) -> str:
        hasher = hashlib.sha256()
        hasher.update(expr.encode("utf-8"))
        hasher.update(b"\x00")
        hasher.update(expected_repr.encode("utf-8"))
        return hasher.hexdigest()[:12]


__all__ = [
    "MetaCalculusPatchGenerator",
    "MetaCalculusPatchCandidate",
]
