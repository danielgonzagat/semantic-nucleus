"""
Tokenizador determinístico mínimo (LxU v0.1).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List

from metanucleus.core.liu import Node, struct, text

TOKEN_RE = re.compile(r"[A-Za-zÀ-ÿ0-9']+|[^\w\s]", re.UNICODE)


@dataclass()
class Token:
    surface: str
    lower: str
    tag: str


def tokenize(raw: str) -> List[Token]:
    tokens: List[Token] = []
    for match in TOKEN_RE.finditer(raw):
        surface = match.group(0)
        lower = surface.lower()
        if surface.isnumeric():
            tag = "NUMBER"
        elif re.fullmatch(r"[^\w\s]", surface):
            tag = "PUNCT"
        else:
            tag = "WORD"
        tokens.append(Token(surface=surface, lower=lower, tag=tag))
    return tokens


def tokens_to_struct(tokens: List[Token]) -> Node:
    fields = {
        f"t{i}": struct(
            surface=text(tok.surface),
            lower=text(tok.lower),
            tag=text(tok.tag),
        )
        for i, tok in enumerate(tokens)
    }
    return struct(**fields)
