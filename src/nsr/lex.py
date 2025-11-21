"""
Lexicalizador universal (LxU) determinístico.
"""

from __future__ import annotations

import re
from typing import List

from .state import Lexicon, Token

WORD_RE = re.compile(r"[\wáéíóúãõâêîôûàèùç_-]+", re.UNICODE)
STOP_WORDS = {
    "o",
    "a",
    "os",
    "as",
    "um",
    "uma",
    "uns",
    "umas",
    "the",
    "an",
}


def tokenize(text: str, lexicon: Lexicon) -> List[Token]:
    tokens: List[Token] = []
    for match in WORD_RE.finditer(text.lower()):
        word = match.group(0)
        if word in STOP_WORDS:
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
        "automobile": "carro",
        "auto": "carro",
        "veículo": "veiculo",
        "veiculo": "veiculo",
        "vehicle": "veiculo",
        "car": "carro",
        "cars": "carro",
    },
    pos_hint={
        "andar": "ACTION",
        "anda": "ACTION",
        "correr": "ACTION",
        "mover": "ACTION",
        "parar": "ACTION",
        "run": "ACTION",
        "move": "ACTION",
        "stop": "ACTION",
        "walk": "ACTION",
    },
    qualifiers={
        "rapido",
        "rápido",
        "devagar",
        "lento",
        "forte",
        "quick",
        "quickly",
        "slow",
        "slowly",
        "fast",
        "strong",
    },
    rel_words={
        "de": "HAS",
        "tem": "HAS",
        "possui": "HAS",
        "com": "HAS",
        "with": "HAS",
        "has": "HAS",
        "have": "HAS",
        "owns": "HAS",
        "of": "HAS",
        "parte": "PART_OF",
        "belongs": "PART_OF",
        "belong": "PART_OF",
    },
)


__all__ = ["tokenize", "DEFAULT_LEXICON"]
