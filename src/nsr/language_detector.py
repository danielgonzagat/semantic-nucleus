"""
Detecção determinística de idioma/dialeto para alimentar o Meta-LER.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, Tuple

from liu import Node, entity, list_node, number, struct as liu_struct, text as liu_text

LANGUAGE_KEYWORDS = {
    "pt": {
        "keywords": {
            "QUE",
            "VOCÊ",
            "VOCE",
            "ESTÁ",
            "ESTA",
            "NÃO",
            "NAO",
            "UMA",
            "UM",
            "CARRO",
            "TEM",
            "SER",
            "ESTOU",
            "ESTAMOS",
        },
        "special": ("Ã", "Õ", "Ç"),
    },
    "en": {
        "keywords": {
            "THE",
            "IS",
            "ARE",
            "CAR",
            "DO",
            "DOES",
            "NOT",
            "HAVE",
            "HAS",
            "YOU",
            "WE",
            "THIS",
            "THAT",
        },
        "special": (),
    },
    "es": {
        "keywords": {
            "QUE",
            "ESTA",
            "ESTÁS",
            "ESTAS",
            "NO",
            "UNA",
            "UN",
            "COCHE",
            "TIENE",
            "HAY",
            "COMO",
        },
        "special": ("Ñ", "Á", "É", "Í", "Ó", "Ú"),
    },
    "fr": {
        "keywords": {
            "QUE",
            "EST",
            "UNE",
            "UN",
            "VOITURE",
            "AVEC",
            "PAS",
            "COMMENT",
            "ÊTRE",
            "ES",
            "SOMMES",
        },
        "special": ("È", "Ê", "Â", "Ô", "Ç"),
    },
    "it": {
        "keywords": {
            "CHE",
            "SEI",
            "SONO",
            "UNA",
            "UN",
            "AUTO",
            "HA",
            "NON",
            "COME",
            "STAI",
            "NOI",
        },
        "special": ("À", "È", "Ì", "Ò", "Ù"),
    },
}

CODE_DIALECTS = {
    "python": {
        "keywords": {"def", "class", "import", "lambda", "self", "None", "True", "False"},
        "markers": ("def ", "class ", "import ", "@dataclass", "async ", "await ", "with "),
    },
    "rust": {
        "keywords": {"fn", "let", "mut", "impl", "crate", "pub", "match", "enum"},
        "markers": ("fn ", "let ", "::", "->", "pub ", "#[derive"),
    },
    "elixir": {
        "keywords": {"def", "defp", "alias", "use", "do", "end", "fn", "iex"},
        "markers": ("defmodule", "def ", "defp ", "|>", "<-", "IO.puts"),
    },
    "javascript": {
        "keywords": {"function", "const", "let", "var", "return", "async", "await"},
        "markers": ("function ", "=>", "const ", "let ", "import ", "export "),
    },
}

WORD_PATTERN = re.compile(r"[A-Za-zÀ-ÿ']+")


@dataclass(frozen=True)
class LanguageDetectionResult:
    category: str
    language: str | None
    confidence: float
    dialect: str | None
    hints: Tuple[str, ...]

    def with_language(self, fallback: str) -> str:
        if self.language:
            return self.language
        return fallback


def detect_language_profile(text_value: str) -> LanguageDetectionResult:
    tokens = tuple(token.upper() for token in WORD_PATTERN.findall(text_value))
    if not tokens and not text_value.strip():
        return LanguageDetectionResult("unknown", None, 0.0, None, ())

    language, lang_score, lang_hints = _detect_natural_language(tokens, text_value)
    code_dialect, code_score, code_hints = _detect_code_dialect(tokens, text_value)

    if code_score > lang_score + 0.05:
        confidence = min(1.0, code_score)
        hints = tuple(code_hints[:6])
        return LanguageDetectionResult("code", language=None, confidence=confidence, dialect=code_dialect, hints=hints)

    if lang_score == 0.0:
        return LanguageDetectionResult("unknown", None, 0.0, None, ())

    hints = tuple(lang_hints[:6])
    return LanguageDetectionResult("text", language=language, confidence=lang_score, dialect=None, hints=hints)


def language_profile_to_node(result: LanguageDetectionResult | None) -> Node | None:
    if result is None:
        return None
    fields: dict[str, Node] = {
        "tag": entity("language_profile"),
        "category": entity(result.category),
        "confidence": number(round(result.confidence, 4)),
    }
    if result.language:
        fields["language"] = entity(result.language.lower())
    if result.dialect:
        fields["dialect"] = entity(result.dialect.lower())
    if result.hints:
        fields["hints"] = list_node(liu_text(hint) for hint in result.hints)
    return liu_struct(**fields)


def _detect_natural_language(tokens: Tuple[str, ...], raw_text: str):
    best_lang = None
    best_score = 0.0
    best_hints: list[str] = []
    token_count = len(tokens) or 1
    for language, profile in LANGUAGE_KEYWORDS.items():
        keyword_hits = [token for token in tokens if token in profile["keywords"]]
        special_hits = _count_special_chars(raw_text, profile["special"])
        score = (len(keyword_hits) + special_hits * 0.3) / token_count
        if score > best_score:
            best_score = score
            best_lang = language
            best_hints = keyword_hits
    return best_lang, min(best_score, 1.0), best_hints


def _detect_code_dialect(tokens: Tuple[str, ...], raw_text: str):
    lowered = raw_text.lower()
    token_count = len(tokens) or 1
    best_dialect = None
    best_score = 0.0
    best_hints: list[str] = []
    for dialect, profile in CODE_DIALECTS.items():
        keyword_hits = [token for token in tokens if token.lower() in profile["keywords"]]
        marker_hits = [marker for marker in profile["markers"] if marker.lower() in lowered]
        score = (len(keyword_hits) + 1.5 * len(marker_hits)) / (token_count + 2)
        if score > best_score:
            best_score = score
            best_dialect = dialect
            best_hints = keyword_hits + marker_hits
    return best_dialect, min(best_score, 1.0), best_hints


def _count_special_chars(text_value: str, specials: Iterable[str]) -> int:
    count = 0
    upper = text_value.upper()
    for special in specials:
        count += upper.count(special)
    return count


__all__ = ["detect_language_profile", "language_profile_to_node", "LanguageDetectionResult"]
