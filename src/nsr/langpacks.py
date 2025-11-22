"""
Recursos linguísticos determinísticos obtidos via ferramentas externas (LLMs, tradutores)
e cristalizados como tabelas estáticas para o núcleo simbólico.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, Tuple


@dataclass(frozen=True)
class LexemeSpec:
    lemma: str
    semantics: str
    pos: str
    forms: Tuple[str, ...]


@dataclass(frozen=True)
class DialogRuleSpec:
    trigger_role: str
    reply_role: str
    reply_semantics: str
    surface_tokens: Tuple[str, ...]
    language: str


@dataclass(frozen=True)
class ConjugationSpec:
    lemma: str
    tense: str
    person: int
    number: str
    form: str


@dataclass(frozen=True)
class LanguagePack:
    code: str
    lexemes: Tuple[LexemeSpec, ...]
    dialog_rules: Tuple[DialogRuleSpec, ...]
    conjugations: Tuple[ConjugationSpec, ...] = ()


def _build_pack(code: str, data: Dict) -> LanguagePack:
    lexemes = tuple(
        LexemeSpec(
            lemma=entry["lemma"],
            semantics=entry["semantics"],
            pos=entry["pos"],
            forms=tuple(entry["forms"]),
        )
        for entry in data.get("lexemes", ())
    )
    dialog_rules = tuple(
        DialogRuleSpec(
            trigger_role=entry["trigger_role"],
            reply_role=entry["reply_role"],
            reply_semantics=entry["reply_semantics"],
            surface_tokens=tuple(entry["surface_tokens"]),
            language=entry["language"],
        )
        for entry in data.get("dialog_rules", ())
    )
    conjugations = tuple(
        ConjugationSpec(
            lemma=entry["lemma"],
            tense=entry["tense"],
            person=entry["person"],
            number=entry["number"],
            form=entry["form"],
        )
        for entry in data.get("conjugations", ())
    )
    return LanguagePack(code=code, lexemes=lexemes, dialog_rules=dialog_rules, conjugations=conjugations)


def get_language_pack(code: str) -> LanguagePack:
    normalized = code.lower()
    if normalized not in LANGUAGE_PACK_DATA:
        raise ValueError(f"Unknown language pack '{code}'")
    if normalized not in _PACK_CACHE:
        _PACK_CACHE[normalized] = _build_pack(normalized, LANGUAGE_PACK_DATA[normalized])
    return _PACK_CACHE[normalized]


def iter_language_packs(codes: Iterable[str]) -> Tuple[LanguagePack, ...]:
    return tuple(get_language_pack(code) for code in codes)


LANGUAGE_PACK_DATA: Dict[str, Dict] = {
    "pt": {
        "lexemes": [
            {"lemma": "OI", "semantics": "GREETING_SIMPLE", "pos": "INTERJ", "forms": ["OI", "OLÁ", "OLA"]},
            {"lemma": "TUDO", "semantics": "ALL_THINGS", "pos": "PRON_INDEF", "forms": ["TUDO"]},
            {"lemma": "BEM", "semantics": "STATE_GOOD", "pos": "ADV", "forms": ["BEM"]},
            {"lemma": "E", "semantics": "CONJ_AND", "pos": "CONJ", "forms": ["E"]},
            {"lemma": "VOCÊ", "semantics": "YOU", "pos": "PRON", "forms": ["VOCÊ", "VOCE"]},
            {"lemma": "EU", "semantics": "SELF", "pos": "PRON", "forms": ["EU"]},
            {"lemma": "SIM", "semantics": "AFFIRM", "pos": "ADV", "forms": ["SIM"]},
            {"lemma": "NÃO", "semantics": "NEGATE", "pos": "ADV", "forms": ["NÃO", "NAO"]},
            {"lemma": "COMO", "semantics": "QUESTION_HOW", "pos": "ADV", "forms": ["COMO"]},
            {"lemma": "ESTAR", "semantics": "BE_STATE", "pos": "VERB", "forms": ["ESTÁ", "ESTA", "ESTOU", "ESTAS"]},
            {"lemma": "MAL", "semantics": "STATE_BAD", "pos": "ADV", "forms": ["MAL"]},
            {"lemma": "RUIM", "semantics": "STATE_BAD", "pos": "ADJ", "forms": ["RUIM"]},
            {"lemma": "TRISTE", "semantics": "STATE_BAD", "pos": "ADJ", "forms": ["TRISTE"]},
        ],
        "dialog_rules": [
            {
                "trigger_role": "QUESTION_HEALTH",
                "reply_role": "ANSWER_HEALTH_AND_RETURN",
                "reply_semantics": "STATE_GOOD_AND_RETURN",
                "surface_tokens": ["tudo", "bem", ",", "e", "você", "?"],
                "language": "pt",
            },
            {
                "trigger_role": "GREETING_SIMPLE",
                "reply_role": "GREETING_SIMPLE_REPLY",
                "reply_semantics": "GREETING_SIMPLE",
                "surface_tokens": ["oi"],
                "language": "pt",
            },
            {
                "trigger_role": "QUESTION_HEALTH_VERBOSE",
                "reply_role": "ANSWER_HEALTH_VERBOSE",
                "reply_semantics": "STATE_GOOD_AND_RETURN",
                "surface_tokens": [":CONJ:estar:pres:1:sing", "bem", ",", "e", "você", "?"],
                "language": "pt",
            },
            {
                "trigger_role": "STATE_POSITIVE",
                "reply_role": "ACK_POSITIVE",
                "reply_semantics": "STATE_POSITIVE_ACK",
                "surface_tokens": ["que", "bom", "!"],
                "language": "pt",
            },
            {
                "trigger_role": "STATE_NEGATIVE",
                "reply_role": "CARE_NEGATIVE",
                "reply_semantics": "STATE_NEGATIVE_SUPPORT",
                "surface_tokens": ["sinto", "muito", ".", "posso", "ajudar", "?"],
                "language": "pt",
            },
        ],
        "conjugations": [
            {"lemma": "estar", "tense": "pres", "person": 1, "number": "sing", "form": "estou"},
            {"lemma": "estar", "tense": "pres", "person": 2, "number": "sing", "form": "está"},
            {"lemma": "estar", "tense": "pres", "person": 3, "number": "sing", "form": "está"},
            {"lemma": "estar", "tense": "pres", "person": 1, "number": "plur", "form": "estamos"},
            {"lemma": "estar", "tense": "pres", "person": 2, "number": "plur", "form": "estão"},
            {"lemma": "estar", "tense": "pres", "person": 3, "number": "plur", "form": "estão"},
        ],
    },
    "en": {
        "lexemes": [
            {"lemma": "HI", "semantics": "GREETING_SIMPLE", "pos": "INTERJ", "forms": ["HI", "HELLO", "HEY"]},
            {"lemma": "FINE", "semantics": "STATE_GOOD", "pos": "ADJ", "forms": ["FINE", "GOOD"]},
            {"lemma": "YOU", "semantics": "YOU", "pos": "PRON", "forms": ["YOU"]},
            {"lemma": "I", "semantics": "SELF", "pos": "PRON", "forms": ["I"]},
            {"lemma": "HOW", "semantics": "QUESTION_HOW", "pos": "ADV", "forms": ["HOW"]},
            {"lemma": "BE", "semantics": "BE_STATE", "pos": "VERB", "forms": ["ARE", "AM", "IS"]},
        ],
        "dialog_rules": [
            {
                "trigger_role": "GREETING_SIMPLE_EN",
                "reply_role": "GREETING_SIMPLE_EN_REPLY",
                "reply_semantics": "GREETING_SIMPLE",
                "surface_tokens": ["hi"],
                "language": "en",
            },
            {
                "trigger_role": "QUESTION_HEALTH_VERBOSE_EN",
                "reply_role": "ANSWER_HEALTH_VERBOSE_EN",
                "reply_semantics": "STATE_GOOD_AND_RETURN",
                "surface_tokens": ["i", "am", "fine", ",", "and", "you", "?"],
                "language": "en",
            },
        ],
        "conjugations": [
            {"lemma": "be", "tense": "pres", "person": 1, "number": "sing", "form": "am"},
            {"lemma": "be", "tense": "pres", "person": 2, "number": "sing", "form": "are"},
            {"lemma": "be", "tense": "pres", "person": 3, "number": "sing", "form": "is"},
        ],
    },
    "es": {
        "lexemes": [
            {"lemma": "HOLA", "semantics": "GREETING_SIMPLE", "pos": "INTERJ", "forms": ["HOLA"]},
            {"lemma": "TODO", "semantics": "ALL_THINGS", "pos": "PRON_INDEF", "forms": ["TODO"]},
            {"lemma": "BIEN", "semantics": "STATE_GOOD", "pos": "ADV", "forms": ["BIEN"]},
            {"lemma": "Y", "semantics": "CONJ_AND", "pos": "CONJ", "forms": ["Y"]},
            {"lemma": "TÚ", "semantics": "YOU", "pos": "PRON", "forms": ["TÚ", "TU"]},
            {"lemma": "COMO", "semantics": "QUESTION_HOW", "pos": "ADV", "forms": ["COMO", "CÓMO"]},
            {"lemma": "ESTAR", "semantics": "BE_STATE", "pos": "VERB", "forms": ["ESTOY", "ESTÁS", "ESTA"]},
        ],
        "dialog_rules": [
            {
                "trigger_role": "QUESTION_HEALTH_ES",
                "reply_role": "ANSWER_HEALTH_ES",
                "reply_semantics": "STATE_GOOD_AND_RETURN",
                "surface_tokens": ["todo", "bien", ",", "y", "tú", "?"],
                "language": "es",
            },
            {
                "trigger_role": "QUESTION_HEALTH_VERBOSE_ES",
                "reply_role": "ANSWER_HEALTH_VERBOSE_ES",
                "reply_semantics": "STATE_GOOD_AND_RETURN",
                "surface_tokens": ["estoy", "bien", ",", "y", "tú", "?"],
                "language": "es",
            },
        ],
        "conjugations": [
            {"lemma": "estar", "tense": "pres", "person": 1, "number": "sing", "form": "estoy"},
            {"lemma": "estar", "tense": "pres", "person": 2, "number": "sing", "form": "estás"},
            {"lemma": "estar", "tense": "pres", "person": 3, "number": "sing", "form": "está"},
        ],
    },
    "fr": {
        "lexemes": [
            {"lemma": "BONJOUR", "semantics": "GREETING_SIMPLE", "pos": "INTERJ", "forms": ["BONJOUR"]},
            {"lemma": "SALUT", "semantics": "GREETING_SIMPLE", "pos": "INTERJ", "forms": ["SALUT"]},
            {"lemma": "TOUT", "semantics": "ALL_THINGS", "pos": "PRON_INDEF", "forms": ["TOUT"]},
            {"lemma": "BIEN", "semantics": "STATE_GOOD", "pos": "ADV", "forms": ["BIEN"]},
            {"lemma": "ET", "semantics": "CONJ_AND", "pos": "CONJ", "forms": ["ET"]},
            {"lemma": "TOI", "semantics": "YOU", "pos": "PRON", "forms": ["TOI"]},
            {"lemma": "COMMENT", "semantics": "QUESTION_HOW", "pos": "ADV", "forms": ["COMMENT"]},
            {"lemma": "ÇA", "semantics": "YOU", "pos": "PRON", "forms": ["ÇA", "CA"]},
            {"lemma": "JE", "semantics": "SELF", "pos": "PRON", "forms": ["JE"]},
            {"lemma": "ALLER", "semantics": "BE_STATE", "pos": "VERB", "forms": ["VA", "VAS", "VAIS"]},
        ],
        "dialog_rules": [
            {
                "trigger_role": "GREETING_SIMPLE_FR",
                "reply_role": "GREETING_SIMPLE_FR_REPLY",
                "reply_semantics": "GREETING_SIMPLE",
                "surface_tokens": ["bonjour"],
                "language": "fr",
            },
            {
                "trigger_role": "QUESTION_HEALTH_FR",
                "reply_role": "ANSWER_HEALTH_FR",
                "reply_semantics": "STATE_GOOD_AND_RETURN",
                "surface_tokens": ["tout", "va", "bien", ",", "et", "toi", "?"],
                "language": "fr",
            },
            {
                "trigger_role": "QUESTION_HEALTH_VERBOSE_FR",
                "reply_role": "ANSWER_HEALTH_VERBOSE_FR",
                "reply_semantics": "STATE_GOOD_AND_RETURN",
                "surface_tokens": ["je", "vais", "bien", ",", "et", "toi", "?"],
                "language": "fr",
            },
        ],
        "conjugations": [
            {"lemma": "aller", "tense": "pres", "person": 1, "number": "sing", "form": "vais"},
            {"lemma": "aller", "tense": "pres", "person": 2, "number": "sing", "form": "vas"},
            {"lemma": "aller", "tense": "pres", "person": 3, "number": "sing", "form": "va"},
        ],
    },
}

_PACK_CACHE: Dict[str, LanguagePack] = {}


__all__ = ["LanguagePack", "LexemeSpec", "DialogRuleSpec", "ConjugationSpec", "get_language_pack", "iter_language_packs"]

