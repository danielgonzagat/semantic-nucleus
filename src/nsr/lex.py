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
        tag, payload = infer_tag(word, lemma, lexicon)
        tokens.append(Token(lemma=lemma, tag=tag, payload=payload))
    return tokens


def infer_tag(word: str, lemma: str, lexicon: Lexicon) -> tuple[str, str | None]:
    rel_label = lexicon.rel_words.get(word) or lexicon.rel_words.get(lemma)
    if rel_label:
        return "RELWORD", rel_label
    if lemma in lexicon.qualifiers or lemma.endswith("mente"):
        return "QUALIFIER", None
    tag = lexicon.pos_hint.get(lemma, "ENTITY")
    return tag, None


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
