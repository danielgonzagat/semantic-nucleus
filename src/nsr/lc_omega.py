"""
LC-Ω – módulo de cálculo linguístico determinístico.
Converte entradas textuais em meta-representação, gera meta-cálculo e sintetiza sentenças.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from typing import Callable, Dict, Iterable, Sequence, Tuple

from .langpacks import LanguagePack, get_language_pack

PUNCTUATION = {".", ",", "?", "!", ";", ":"}
TOKEN_PATTERN = re.compile(r"[\wÀ-ÿ']+|[.,?!]", re.UNICODE)
STATE_VALUES = {"STATE_GOOD", "STATE_BAD"}
ENTITY_PRIORITY = ("SELF", "YOU", "ALL_THINGS")
LANG_CODE_MAX = 3


@dataclass(frozen=True)
class LCTerm:
    kind: str
    label: str | None = None
    children: Tuple["LCTerm", ...] = ()


@dataclass(frozen=True)
class MetaCalculation:
    operator: str
    operands: Tuple[LCTerm, ...] = ()

    def as_term(self) -> LCTerm:
        return LCTerm(kind="CALC", label=self.operator, children=self.operands)


@dataclass(frozen=True)
class LCParseResult:
    language: str
    original_text: str
    tokens: Tuple[str, ...]
    semantics: Tuple[str, ...]
    pattern: str | None
    term: LCTerm
    calculus: MetaCalculation | None


def lc_term_from_pattern(language: str, pattern_name: str) -> LCTerm:
    pack = get_language_pack(language)
    pattern = _find_pattern(pack, pattern_name)
    if pattern is None:
        raise ValueError(f"Pattern '{pattern_name}' not found for language '{language}'.")
    return _term_from_semantics(pattern.sequence)


def lc_parse(language: str, text: str) -> LCParseResult:
    pack = get_language_pack(language)
    tokens = _tokenize(text)
    semantics = _semantics_from_tokens(pack, tokens)
    term = lc_normalize(_term_from_semantics(semantics))
    pattern = _match_pattern(pack, semantics)
    calculus = _derive_calculus(pattern, term)
    return LCParseResult(
        language=language,
        original_text=text,
        tokens=tokens,
        semantics=semantics,
        pattern=pattern,
        term=term,
        calculus=calculus,
    )


def lc_normalize(term: LCTerm) -> LCTerm:
    if term.kind != "SEQ":
        return term
    builder = []
    for child in term.children:
        if not builder or builder[-1] != child:
            builder.append(child)
    return LCTerm(kind="SEQ", children=tuple(builder))


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


def _tokenize(text: str) -> Tuple[str, ...]:
    return tuple(match.group(0).strip().lower() for match in TOKEN_PATTERN.finditer(text) if match.group(0).strip())


def _semantics_from_tokens(pack: LanguagePack, tokens: Sequence[str]) -> Tuple[str, ...]:
    stopwords = _stopwords(pack.code)
    form_index = _form_index(pack.code)
    semantics: list[str] = []
    for token in tokens:
        upper = token.upper()
        if upper in stopwords or upper in PUNCTUATION:
            continue
        if upper.isdigit():
            semantics.append(f"NUM:{upper}")
            continue
        semantics.append(form_index.get(upper, f"LIT:{upper}"))
    return tuple(semantics)


def _match_pattern(pack: LanguagePack, semantics: Sequence[str]) -> str | None:
    for pattern in pack.syntactic_patterns:
        if tuple(pattern.sequence) == tuple(semantics):
            return pattern.name
    return None


def _derive_calculus(pattern: str | None, term: LCTerm) -> MetaCalculation | None:
    if pattern is None:
        return None
    canonical = _canonical_pattern_name(pattern)
    builder = PATTERN_CALCULUS_BUILDERS.get(canonical)
    if not builder:
        return None
    return builder(term)


def _term_from_semantics(semantics: Sequence[str]) -> LCTerm:
    return LCTerm(kind="SEQ", children=tuple(LCTerm(kind="SYM", label=item) for item in semantics))


def _state_query(term: LCTerm) -> MetaCalculation:
    equation = _state_equation(term, relation="?")
    return MetaCalculation(operator="STATE_QUERY", operands=(equation,))


def _state_assert(term: LCTerm) -> MetaCalculation:
    equation = _state_equation(term, relation="=")
    return MetaCalculation(operator="STATE_ASSERT", operands=(equation,))


def _emit_calc(tag: str) -> Callable[[LCTerm], MetaCalculation]:
    def _builder(term: LCTerm) -> MetaCalculation:
        return MetaCalculation(operator=tag, operands=(term,))

    return _builder


def _command_calc(term: LCTerm) -> MetaCalculation:
    return MetaCalculation(operator="COMMAND_ROUTE", operands=(term,))


def _fact_query(term: LCTerm) -> MetaCalculation:
    focus = _first_literal(term) or LCTerm(kind="SYM", label="FACT")
    query_term = LCTerm(kind="FACT_QUERY", label="REQUEST", children=(focus,))
    return MetaCalculation(operator="FACT_QUERY", operands=(query_term,))


def _first_literal(term: LCTerm) -> LCTerm | None:
    for child in term.children:
        if child.label and child.label.startswith("LIT:"):
            return child
    return None


def _state_equation(term: LCTerm, relation: str) -> LCTerm:
    entity = _find_entity(term) or LCTerm(kind="SYM", label="YOU")
    value = _find_state_value(term)
    lhs = LCTerm(kind="OP", label="STATE_OF", children=(entity,))
    if value is None and relation == "?":
        return _equation_term(relation, lhs)
    rhs = value or LCTerm(kind="SYM", label="STATE_UNKNOWN")
    return _equation_term(relation, lhs, rhs)


def _find_entity(term: LCTerm) -> LCTerm | None:
    for desired in ENTITY_PRIORITY:
        for child in term.children:
            if child.label == desired:
                return child
    return None


def _find_state_value(term: LCTerm) -> LCTerm | None:
    for child in term.children:
        if child.label in STATE_VALUES:
            return child
    for child in term.children:
        if child.label == "BE_STATE":
            return LCTerm(kind="SYM", label="STATE_UNSPECIFIED")
    return None


def _equation_term(relation: str, left: LCTerm, right: LCTerm | None = None) -> LCTerm:
    if right is None:
        return LCTerm(kind="EQ", label=relation, children=(left,))
    return LCTerm(kind="EQ", label=relation, children=(left, right))


def _canonical_pattern_name(name: str) -> str:
    head, sep, tail = name.rpartition("_")
    if sep and tail.isalpha() and tail.isupper() and 2 <= len(tail) <= LANG_CODE_MAX:
        return head
    return name


def _build_semantics_map(pack: LanguagePack) -> Dict[str, "LexemeProxy"]:
    mapping: Dict[str, LexemeProxy] = {}
    for lex in pack.lexemes:
        mapping.setdefault(lex.semantics, LexemeProxy(lemma=lex.lemma, forms=lex.forms))
    return mapping


@lru_cache(maxsize=32)
def _form_index(language: str) -> Dict[str, str]:
    pack = get_language_pack(language)
    mapping: Dict[str, str] = {}
    for lex in pack.lexemes:
        for form in lex.forms:
            mapping[form.upper()] = lex.semantics
    for conj in pack.conjugations:
        key = conj.form.upper()
        mapping.setdefault(key, f"CONJ:{conj.lemma}:{conj.tense}:{conj.person}:{conj.number}".upper())
    return mapping


@lru_cache(maxsize=32)
def _stopwords(language: str) -> frozenset[str]:
    pack = get_language_pack(language)
    return frozenset(word.upper() for word in pack.stopwords)


def _find_pattern(pack: LanguagePack, name: str):
    for pattern in pack.syntactic_patterns:
        if pattern.name == name:
            return pattern
    return None


@dataclass(frozen=True)
class LexemeProxy:
    lemma: str
    forms: Tuple[str, ...]


PATTERN_CALCULUS_BUILDERS: Dict[str, Callable[[LCTerm], MetaCalculation]] = {
    "QUESTION_HEALTH": _state_query,
    "QUESTION_HEALTH_VERBOSE": _state_query,
    "ANSWER_HEALTH": _state_assert,
    "ANSWER_HEALTH_VERBOSE": _state_assert,
    "GREETING_SIMPLE": _emit_calc("EMIT_GREETING"),
    "THANKS": _emit_calc("EMIT_THANKS"),
    "FAREWELL": _emit_calc("EMIT_FAREWELL"),
    "CONFIRM": _emit_calc("EMIT_CONFIRM"),
    "QUESTION_FACT": _fact_query,
    "COMMAND": _command_calc,
}


__all__ = [
    "LCTerm",
    "MetaCalculation",
    "LCParseResult",
    "lc_term_from_pattern",
    "lc_parse",
    "lc_normalize",
    "lc_synthesize",
]
