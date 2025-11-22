"""
Adaptadores de entrada determinísticos (versão mínima).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from metanucleus.core.liu import Node, text
from metanucleus.lang.lxu_pse import parse_utterance


class InputKind(str, Enum):
    TEXT = "text"
    CONTROL = "control"
    UNKNOWN = "unknown"


def classify_input(raw: str) -> InputKind:
    stripped = raw.strip()
    if not stripped:
        return InputKind.UNKNOWN
    if stripped.startswith("/"):
        return InputKind.CONTROL
    return InputKind.TEXT


@dataclass(slots=True)
class TextInputAdapter:
    default_lang: str = "pt"

    def to_liu(self, raw: str, lang: str | None = None) -> Node:
        utterance = parse_utterance(raw)
        language = (lang or self.default_lang).lower()
        utterance.fields["lang"] = text(language)
        # compat: garantir campo content
        if "content" not in utterance.fields:
            utterance.fields["content"] = text(raw)
        return utterance
