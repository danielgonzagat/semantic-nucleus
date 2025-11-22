"""
LC-Ω – módulo de cálculo linguístico determinístico.
Converte padrões sintáticos em termos algébricos e sintetiza sentenças por idioma.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, Tuple

from .langpacks import LanguagePack, get_language_pack


@dataclass(frozen=True)
class LCTerm:
    kind: str
    label: str | None = None
    children: Tuple["LCTerm", ...] = ()


def lc_term_from_pattern(language: str, pattern_name: str) -> LCTerm:
    pack = get_language_pack(language)
    pattern = _find_pattern(pack, pattern_name)
    if pattern is None:
        raise ValueError(f"Pattern '{pattern_name}' not found for language '{language}'.")
    items = tuple(LCTerm(kind="SYM", label=semantic) for semantic in pattern.sequence)
    return LCTerm(kind="SEQ", children=items)


def lc_normalize(term: LCTerm) -> LCTerm:
    if term.kind != "SEQ":
        return term
    seen = []
    for child in term.children:
        if not seen or seen[-1] != child:
            seen.append(child)
    return LCTerm(kind="SEQ", children=tuple(seen))


def lc_synthesize(term: LCTerm, language: str) -> Tuple[str, ...]:
    pack = get_language_pack(language)
    semantics_map = _build_semantics_map(pack)
    tokens = []
    for child in term.children:
        if child.kind != "SYM":
            continue
        semantics = child.label or ""
        lex = semantics_map.get(semantics)
        if lex:
            tokens.append(lex.forms[0].lower())
        else:
            tokens.append(semantics.lower())
    return tuple(tokens)


def _find_pattern(pack: LanguagePack, name: str):
    for pattern in pack.syntactic_patterns:
        if pattern.name == name:
            return pattern
    return None


def _build_semantics_map(pack: LanguagePack) -> Dict[str, "LexemeProxy"]:
    mapping: Dict[str, LexemeProxy] = {}
    for lex in pack.lexemes:
        mapping.setdefault(lex.semantics, LexemeProxy(lemma=lex.lemma, forms=lex.forms))
    return mapping


@dataclass(frozen=True)
class LexemeProxy:
    lemma: str
    forms: Tuple[str, ...]


__all__ = ["LCTerm", "lc_term_from_pattern", "lc_normalize", "lc_synthesize"]
