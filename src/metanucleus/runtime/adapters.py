"""
Adaptadores de entrada determinísticos (versão mínima).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from metanucleus.core.liu import Node, text, struct
from metanucleus.lang.lxu_pse import parse_utterance


class InputKind(str, Enum):
    TEXT = "text"
    CODE = "code"
    CONTROL = "control"
    UNKNOWN = "unknown"


def classify_input(raw: str) -> InputKind:
    stripped = raw.strip()
    if not stripped:
        return InputKind.UNKNOWN
    if stripped.startswith("/"):
        return InputKind.CONTROL
    if _looks_like_code(stripped):
        return InputKind.CODE
    return InputKind.TEXT


@dataclass(slots=True)
class TextInputAdapter:
    default_lang: str = "pt"

    def to_liu(self, raw: str, lang: str | None = None) -> Node:
        utterance = parse_utterance(raw)
        if lang:
            utterance.fields["lang"] = text(lang.lower())
        elif "lang" not in utterance.fields or not utterance.fields["lang"].label:
            utterance.fields["lang"] = text(self.default_lang)
        if "content" not in utterance.fields:
            utterance.fields["content"] = text(raw)
        return utterance


@dataclass(slots=True)
class CodeInputAdapter:
    language: str = "python"

    def to_liu(self, raw: str) -> Node:
        from metanucleus.core.ast_bridge import python_code_to_liu

        code_ast = python_code_to_liu(raw)
        return struct(
            kind=text("code_snippet"),
            lang=text("code"),
            content=text(raw),
            intent=text("statement"),
            code_lang=text(self.language),
            ast=code_ast,
        )


def _looks_like_code(text_input: str) -> bool:
    starts = ("def ", "class ", "import ", "from ", "async def ")
    return text_input.startswith(starts)
