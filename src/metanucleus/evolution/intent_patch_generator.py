"""
Gerador de patches para `intent_lexicon.json` usando logs de mismatches.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from metanucleus.evolution.diff_utils import make_unified_diff
from metanucleus.evolution.intent_mismatch_log import (
    INTENT_MISMATCH_LOG_PATH,
    IntentMismatchLogEntry,
    load_intent_mismatch_logs,
)
from metanucleus.semantics.intent_lexicon import (
    add_pattern,
    extract_candidate_patterns,
    load_intent_lexicon,
)
from metanucleus.utils.project import get_project_root


@dataclass()
class IntentLexiconPatchCandidate:
    title: str
    description: str
    diff: str


class IntentLexiconPatchGenerator:
    """
    Analisa `intent_mismatches.jsonl` e sugere patches para o léxico.
    """

    def __init__(
        self,
        project_root: Optional[Path] = None,
        lexicon_path: Optional[Path] = None,
        log_path: Optional[Path] = None,
        log_limit: Optional[int] = None,
        default_lang: str = "pt",
    ) -> None:
        self.project_root = project_root or get_project_root(Path(__file__))
        self.lexicon_path = lexicon_path or (
            self.project_root / "src" / "metanucleus" / "data" / "intent_lexicon.json"
        )
        self.log_path = log_path or INTENT_MISMATCH_LOG_PATH
        self.log_limit = log_limit
        self.default_lang = default_lang

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    def generate_patches(self, max_candidates: int = 1) -> List[IntentLexiconPatchCandidate]:
        lexicon = load_intent_lexicon(self.lexicon_path)
        mismatches = load_intent_mismatch_logs(limit=self.log_limit, path=self.log_path)
        if not mismatches:
            return []

        suggestions = self._collect_suggestions(mismatches)
        if not suggestions:
            return []

        original_text = (
            self.lexicon_path.read_text(encoding="utf-8")
            if self.lexicon_path.exists()
            else json.dumps({}, ensure_ascii=False, indent=2)
        )

        lexicon_copy = json.loads(json.dumps(lexicon, ensure_ascii=False))
        changed = False
        for (lang, intent), patterns in suggestions.items():
            for pattern in patterns:
                before = len(lexicon_copy.get(lang, {}).get(intent, []))
                add_pattern(lexicon_copy, lang, intent, pattern)
                after = len(lexicon_copy.get(lang, {}).get(intent, []))
                if after > before:
                    changed = True

        if not changed:
            return []

        patched_text = json.dumps(lexicon_copy, ensure_ascii=False, indent=2, sort_keys=True)
        diff = make_unified_diff(
            filename=str(self.lexicon_path.relative_to(self.project_root)),
            original=original_text,
            patched=patched_text,
        )
        if not diff.strip():
            return []

        description_lines = [
            "Padrões adicionados automaticamente com base em mismatches:",
        ]
        for (lang, intent), patterns in list(suggestions.items())[:5]:
            joined = ", ".join(patterns[:5])
            description_lines.append(f"- {lang}/{intent}: {joined}")

        candidate = IntentLexiconPatchCandidate(
            title="Auto-evolution: atualizar intent_lexicon.json",
            description="\n".join(description_lines),
            diff=diff,
        )
        return [candidate][:max_candidates]

    # ------------------------------------------------------------------
    # Internos
    # ------------------------------------------------------------------

    def _collect_suggestions(
        self,
        mismatches: List[IntentMismatchLogEntry],
    ) -> Dict[Tuple[str, str], List[str]]:
        grouped: Dict[Tuple[str, str], List[str]] = {}
        for entry in mismatches:
            lang = (entry.lang or self.default_lang).lower()
            intent = entry.expected_intent.lower()
            patterns = extract_candidate_patterns(entry.text)
            key = (lang, intent)
            bucket = grouped.setdefault(key, [])
            for pattern in patterns:
                norm = pattern.strip().lower()
                if norm and norm not in bucket:
                    bucket.append(norm)
        return grouped


__all__ = ["IntentLexiconPatchGenerator", "IntentLexiconPatchCandidate"]
