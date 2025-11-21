"""
Lexicalizador universal (LxU) determinístico.
"""

from __future__ import annotations

import re
from typing import List

from .state import Lexicon, Token

WORD_RE = re.compile(r"[\wáéíóúãõâêîôûàèùç_-]+", re.UNICODE)


def tokenize(text: str, lexicon: Lexicon) -> List[Token]:
    tokens: List[Token] = []
    for match in WORD_RE.finditer(text.lower()):
        word = match.group(0)
        if word in {"o", "a", "os", "as"}:
            continue
        lemma = lexicon.synonyms.get(word, word)
        tag = infer_tag(lemma, lexicon)
        tokens.append(Token(lemma=lemma, tag=tag))
    return tokens


def infer_tag(word: str, lexicon: Lexicon) -> str:
    if word in lexicon.qualifiers or word.endswith("mente"):
        return "QUALIFIER"
    if word in lexicon.rel_words:
        return "RELWORD"
    return lexicon.pos_hint.get(word, "ENTITY")


DEFAULT_LEXICON = Lexicon(
    synonyms={
        "automovel": "carro",
        "automóvel": "carro",
        "veículo": "veiculo",
        "car": "carro",
    },
    pos_hint={
        "andar": "ACTION",
        "anda": "ACTION",
        "correr": "ACTION",
        "mover": "ACTION",
        "parar": "ACTION",
    },
    qualifiers={"rapido", "rápido", "devagar", "lento", "forte"},
    rel_words={"de": "HAS", "tem": "HAS", "possui": "HAS", "parte": "PART_OF"},
)


__all__ = ["tokenize", "DEFAULT_LEXICON"]
