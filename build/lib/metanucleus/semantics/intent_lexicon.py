"""
APIs determinísticas para carregar, inspecionar e evoluir o léxico de intents.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from metanucleus.utils.project import get_project_root

IntentLexicon = Dict[str, Dict[str, List[str]]]

_PROJECT_ROOT = get_project_root(Path(__file__))
_DATA_DIR = _PROJECT_ROOT / "src" / "metanucleus" / "data"
_DEFAULT_LEXICON_PATH = _DATA_DIR / "intent_lexicon.json"
_DEFAULT_LANG = "pt"


# ---------------------------------------------------------------------------
# Persistência
# ---------------------------------------------------------------------------


def load_intent_lexicon(path: Optional[Path] = None) -> IntentLexicon:
    lex_path = path or _DEFAULT_LEXICON_PATH
    if not lex_path.exists():
        return {}
    raw = json.loads(lex_path.read_text(encoding="utf-8"))
    lexicon: IntentLexicon = {}
    for lang, intents in raw.items():
        lang_map: Dict[str, List[str]] = {}
        for intent_name, patterns in intents.items():
            lang_map[str(intent_name)] = [str(p) for p in patterns]
        lexicon[str(lang)] = lang_map
    return lexicon


def save_intent_lexicon(lexicon: IntentLexicon, path: Optional[Path] = None) -> None:
    lex_path = path or _DEFAULT_LEXICON_PATH
    lex_path.parent.mkdir(parents=True, exist_ok=True)
    lex_path.write_text(
        json.dumps(lexicon, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# Atualização
# ---------------------------------------------------------------------------


def add_pattern(lexicon: IntentLexicon, lang: str, intent: str, pattern: str) -> IntentLexicon:
    lang = lang.lower()
    intent = intent.lower()
    norm = pattern.strip()
    if not norm:
        return lexicon

    lang_bucket = lexicon.setdefault(lang, {})
    existing = lang_bucket.setdefault(intent, [])
    if norm.lower() not in {p.lower() for p in existing}:
        existing.append(norm)
    return lexicon


# ---------------------------------------------------------------------------
# Matching
# ---------------------------------------------------------------------------


def match_intent_from_lexicon(text: str, lexicon: IntentLexicon, lang: str) -> Optional[str]:
    text_lower = text.lower().strip()
    intents = lexicon.get(lang.lower())
    if not intents:
        return None
    for intent_name, patterns in intents.items():
        for pattern in patterns:
            if pattern.lower() in text_lower:
                return intent_name
    return None


def detect_language(text: str, lexicon: IntentLexicon, default: str = _DEFAULT_LANG) -> str:
    if not text.strip():
        return default
    text_lower = text.lower()
    scores: Dict[str, int] = {}
    for lang, intents in lexicon.items():
        score = 0
        for patterns in intents.values():
            for pattern in patterns:
                if pattern.lower() in text_lower:
                    score += 1
        scores[lang] = score

    if all(score == 0 for score in scores.values()):
        return default

    best_score = max(scores.values())
    candidates = [lang for lang, score in scores.items() if score == best_score]
    default_lower = default.lower()
    if default_lower in candidates:
        return default_lower
    return sorted(candidates)[0]


def infer_intent(
    text: str,
    lexicon: IntentLexicon,
    lang_hint: Optional[str] = None,
    default_lang: str = _DEFAULT_LANG,
) -> Tuple[Optional[str], Optional[str]]:
    if not text.strip():
        return None, None
    lang = (lang_hint or detect_language(text, lexicon, default=default_lang)).lower()
    intent = match_intent_from_lexicon(text, lexicon, lang)
    return lang, intent


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------


def extract_candidate_patterns(text: str) -> List[str]:
    """
    Heurística determinística para sugerir novos padrões, usada em autoevolução.
    Retorna prefixos de 1 e 2 tokens.
    """
    cleaned = re.sub(r"[?!.,;:]+", " ", text.lower())
    tokens = [tok for tok in cleaned.split() if tok]
    if not tokens:
        return []
    patterns = [tokens[0]]
    if len(tokens) >= 2:
        patterns.append(" ".join(tokens[:2]))
    return patterns


__all__ = [
    "IntentLexicon",
    "load_intent_lexicon",
    "save_intent_lexicon",
    "add_pattern",
    "match_intent_from_lexicon",
    "detect_language",
    "infer_intent",
    "extract_candidate_patterns",
]
