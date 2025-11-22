"""
Adaptadores de entrada determinísticos (versão mínima).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from metanucleus.core.liu import Node, struct, text


class InputKind(str, Enum):
    TEXT = "text"
    UNKNOWN = "unknown"


def classify_input(raw: str) -> InputKind:
    stripped = raw.strip()
    if not stripped:
        return InputKind.UNKNOWN
    return InputKind.TEXT


@dataclass(slots=True)
class TextInputAdapter:
    default_lang: str = "pt"

    def to_liu(self, raw: str, lang: str | None = None) -> Node:
        language = (lang or self.default_lang).lower()
        return struct(
            kind=text("utterance"),
            lang=text(language),
            content=text(raw),
        )
