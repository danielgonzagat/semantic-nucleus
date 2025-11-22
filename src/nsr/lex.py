"""
Lexicalizador universal (LxU) determinístico.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import List, Sequence

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
    "el",
    "la",
    "los",
    "las",
    "lo",
    "uno",
    "una",
    "unos",
    "unas",
    "un",
    "une",
    "des",
    "les",
    "le",
    "du",
    "gli",
    "degli",
    "delle",
    "della",
    "dello",
    "the",
    "an",
}


def tokenize(text: str, lexicon: Lexicon) -> List[Token]:
    tokens: List[Token] = []
    for match in WORD_RE.finditer(text.lower()):
        word = match.group(0)
        lemma = lexicon.synonyms.get(word, word)
        tag, payload = infer_tag(word, lemma, lexicon)
        if word in STOP_WORDS and tag == "ENTITY":
            continue
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


def compose_lexicon(language_codes: Sequence[str]) -> Lexicon:
    lex = Lexicon()
    for code in language_codes:
        pack = LANGUAGE_PACKS.get(code.lower())
        if pack is None:
            raise ValueError(f"Unknown language pack '{code}'")
        lex = lex.merge(pack)
    return lex


def load_lexicon_file(path: str | Path) -> Lexicon:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return Lexicon.from_mapping(data)


LANGUAGE_PACKS: dict[str, Lexicon] = {
    "pt": Lexicon(
        synonyms={
            "automovel": "carro",
            "automóvel": "carro",
            "veículo": "veiculo",
            "veiculo": "veiculo",
        },
        pos_hint={
            "andar": "ACTION",
            "anda": "ACTION",
            "correr": "ACTION",
            "mover": "ACTION",
            "parar": "ACTION",
        },
        qualifiers={
            "rapido",
            "rápido",
            "devagar",
            "lento",
            "forte",
        },
        rel_words={
            "de": "HAS",
            "tem": "HAS",
            "possui": "HAS",
            "com": "HAS",
            "parte": "PART_OF",
        },
    ),
    "en": Lexicon(
        synonyms={
            "automobile": "carro",
            "auto": "carro",
            "vehicle": "veiculo",
            "car": "carro",
            "cars": "carro",
        },
        pos_hint={
            "run": "ACTION",
            "move": "ACTION",
            "stop": "ACTION",
            "walk": "ACTION",
        },
        qualifiers={
            "quick",
            "quickly",
            "slow",
            "slowly",
            "fast",
            "strong",
        },
        rel_words={
            "with": "HAS",
            "has": "HAS",
            "have": "HAS",
            "owns": "HAS",
            "own": "HAS",
            "of": "HAS",
            "belongs": "PART_OF",
            "belong": "PART_OF",
        },
    ),
    "es": Lexicon(
        synonyms={
            "automovil": "carro",
            "automóvil": "carro",
            "coche": "carro",
            "carro": "carro",
            "vehiculo": "veiculo",
            "vehículo": "veiculo",
            "rueda": "roda",
        },
        pos_hint={
            "mover": "ACTION",
            "mueve": "ACTION",
            "corre": "ACTION",
            "andar": "ACTION",
            "camina": "ACTION",
        },
        qualifiers={
            "rápido",
            "rapido",
            "lentamente",
            "rapidamente",
            "fuerte",
        },
        rel_words={
            "con": "HAS",
            "tiene": "HAS",
            "tienen": "HAS",
            "posee": "HAS",
            "pertenece": "PART_OF",
            "pertenecen": "PART_OF",
        },
    ),
    "fr": Lexicon(
        synonyms={
            "voiture": "carro",
            "auto": "carro",
            "automobile": "carro",
            "véhicule": "veiculo",
            "vehicule": "veiculo",
            "roue": "roda",
        },
        pos_hint={
            "bouge": "ACTION",
            "marche": "ACTION",
            "course": "ACTION",
            "avance": "ACTION",
        },
        qualifiers={
            "rapide",
            "rapidement",
            "lent",
            "lentement",
            "fort",
        },
        rel_words={
            "avec": "HAS",
            "possède": "HAS",
            "possede": "HAS",
            "a": "HAS",
            "appartient": "PART_OF",
        },
    ),
      "it": Lexicon(
          synonyms={
              "auto": "carro",
              "automobile": "carro",
              "macchina": "carro",
              "veicolo": "veiculo",
              "ruota": "roda",
          },
          pos_hint={
              "muove": "ACTION",
              "muovere": "ACTION",
              "corre": "ACTION",
              "cammina": "ACTION",
              "camminare": "ACTION",
          },
          qualifiers={
              "veloce",
              "rapido",
              "lentamente",
              "forte",
          },
          rel_words={
              "con": "HAS",
              "ha": "HAS",
              "hanno": "HAS",
              "possiede": "HAS",
              "appartiene": "PART_OF",
          },
      ),
}


DEFAULT_LEXICON = compose_lexicon(("pt", "en", "es", "fr", "it"))


__all__ = ["tokenize", "DEFAULT_LEXICON", "compose_lexicon", "load_lexicon_file", "LANGUAGE_PACKS"]
