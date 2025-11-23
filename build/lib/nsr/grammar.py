"""
Perfis gramaticais determinísticos para o parser sintático multidioma.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Mapping


@dataclass(frozen=True)
class PronounInfo:
    lemma: str
    role: str  # "subject" | "object" | "both"
    person: str | None = None
    number: str | None = None


@dataclass(frozen=True)
class GrammarProfile:
    code: str
    negations: frozenset[str]
    question_words: frozenset[str]
    imperative_markers: frozenset[str]
    pronouns: Mapping[str, PronounInfo]
    auxiliaries: frozenset[str]

    def pronoun_for(self, lemma: str) -> PronounInfo | None:
        return self.pronouns.get(lemma.lower())


def _lower_set(words: Dict[str, str] | Mapping[str, str] | frozenset[str] | set[str] | list[str] | tuple[str, ...]) -> frozenset[str]:
    return frozenset({str(word).lower() for word in words})


def _build_pronouns(entries: Dict[str, Dict[str, object]]) -> Dict[str, PronounInfo]:
    table: Dict[str, PronounInfo] = {}
    for lemma, payload in entries.items():
        role = payload.get("role", "subject")
        person = payload.get("person")
        number = payload.get("number")
        aliases = payload.get("aliases", [])
        info = PronounInfo(lemma=lemma.lower(), role=str(role), person=person, number=number)
        keys = {lemma.lower(), *(alias.lower() for alias in aliases)}
        for key in keys:
            table[key] = info
    return table


LANGUAGE_GRAMMAR: Dict[str, GrammarProfile] = {}


def _register_profile(
    code: str,
    *,
    negations: Mapping[str, object] | set[str] | list[str] | tuple[str, ...],
    question_words: Mapping[str, object] | set[str] | list[str] | tuple[str, ...],
    imperative_markers: Mapping[str, object] | set[str] | list[str] | tuple[str, ...],
    pronouns: Dict[str, Dict[str, object]],
    auxiliaries: Mapping[str, object] | set[str] | list[str] | tuple[str, ...] | None = None,
) -> None:
    LANGUAGE_GRAMMAR[code] = GrammarProfile(
        code=code,
        negations=_lower_set(negations),
        question_words=_lower_set(question_words),
        imperative_markers=_lower_set(imperative_markers),
        pronouns=_build_pronouns(pronouns),
        auxiliaries=_lower_set(auxiliaries or ()),
    )


_register_profile(
    "pt",
    negations={"não", "nao", "jamais", "nunca"},
    question_words={"quem", "quando", "onde", "como", "qual", "quais", "por que", "porque", "que"},
    imperative_markers={"faça", "faca", "por favor", "preciso", "execute", "calcule", "resolva"},
    pronouns={
        "eu": {"role": "subject", "person": "1", "number": "sing"},
        "tu": {"role": "subject", "person": "2", "number": "sing"},
        "você": {"role": "subject", "person": "2", "number": "sing", "aliases": ["voce"]},
        "ele": {"role": "subject", "person": "3", "number": "sing"},
        "ela": {"role": "subject", "person": "3", "number": "sing"},
        "nós": {"role": "subject", "person": "1", "number": "plur", "aliases": ["nos"]},
        "vocês": {"role": "subject", "person": "2", "number": "plur", "aliases": ["voces"]},
        "eles": {"role": "subject", "person": "3", "number": "plur"},
        "elas": {"role": "subject", "person": "3", "number": "plur"},
        "me": {"role": "object", "person": "1", "number": "sing"},
        "mim": {"role": "object", "person": "1", "number": "sing"},
        "te": {"role": "object", "person": "2", "number": "sing"},
        "lhe": {"role": "object", "person": "3", "number": "sing"},
        "nos": {"role": "both", "person": "1", "number": "plur"},
        "vos": {"role": "both", "person": "2", "number": "plur"},
    },
)

_register_profile(
    "en",
    negations={"not", "never", "no"},
    question_words={"who", "what", "when", "where", "why", "how", "which"},
    imperative_markers={"please", "do", "run", "compute", "calculate"},
    pronouns={
        "i": {"role": "subject", "person": "1", "number": "sing"},
        "you": {"role": "both", "person": "2", "number": "sing"},
        "he": {"role": "subject", "person": "3", "number": "sing"},
        "she": {"role": "subject", "person": "3", "number": "sing"},
        "it": {"role": "subject", "person": "3", "number": "sing"},
        "we": {"role": "subject", "person": "1", "number": "plur"},
        "they": {"role": "subject", "person": "3", "number": "plur"},
        "me": {"role": "object", "person": "1", "number": "sing"},
        "us": {"role": "object", "person": "1", "number": "plur"},
        "them": {"role": "object", "person": "3", "number": "plur"},
        "him": {"role": "object", "person": "3", "number": "sing"},
        "her": {"role": "object", "person": "3", "number": "sing"},
    },
    auxiliaries={"do", "does", "did"},
)

_register_profile(
    "es",
    negations={"no", "nunca", "jamás", "jamas"},
    question_words={"quién", "quien", "qué", "que", "dónde", "donde", "cuándo", "cuando", "por qué", "porque", "cómo", "como"},
    imperative_markers={"haz", "haga", "por favor", "calcula", "ejecuta"},
    pronouns={
        "yo": {"role": "subject", "person": "1", "number": "sing"},
        "tú": {"role": "subject", "person": "2", "number": "sing", "aliases": ["tu"]},
        "usted": {"role": "subject", "person": "2", "number": "sing"},
        "él": {"role": "subject", "person": "3", "number": "sing", "aliases": ["el"]},
        "ella": {"role": "subject", "person": "3", "number": "sing"},
        "nosotros": {"role": "subject", "person": "1", "number": "plur"},
        "nosotras": {"role": "subject", "person": "1", "number": "plur"},
        "vosotros": {"role": "subject", "person": "2", "number": "plur"},
        "ustedes": {"role": "subject", "person": "2", "number": "plur"},
        "ellos": {"role": "subject", "person": "3", "number": "plur"},
        "ellas": {"role": "subject", "person": "3", "number": "plur"},
        "me": {"role": "object", "person": "1", "number": "sing"},
        "te": {"role": "object", "person": "2", "number": "sing"},
        "lo": {"role": "object", "person": "3", "number": "sing"},
        "la": {"role": "object", "person": "3", "number": "sing"},
        "nos": {"role": "both", "person": "1", "number": "plur"},
        "os": {"role": "object", "person": "2", "number": "plur"},
    },
)

_register_profile(
    "fr",
    negations={"ne", "pas", "jamais"},
    question_words={"qui", "quoi", "comment", "pourquoi", "quand", "où", "ou", "lequel"},
    imperative_markers={"veuillez", "merci de", "fais", "faites", "exécute", "execute"},
    pronouns={
        "je": {"role": "subject", "person": "1", "number": "sing"},
        "tu": {"role": "subject", "person": "2", "number": "sing"},
        "il": {"role": "subject", "person": "3", "number": "sing"},
        "elle": {"role": "subject", "person": "3", "number": "sing"},
        "nous": {"role": "subject", "person": "1", "number": "plur"},
        "vous": {"role": "both", "person": "2", "number": "plur"},
        "ils": {"role": "subject", "person": "3", "number": "plur"},
        "elles": {"role": "subject", "person": "3", "number": "plur"},
        "moi": {"role": "object", "person": "1", "number": "sing"},
        "toi": {"role": "object", "person": "2", "number": "sing"},
        "lui": {"role": "object", "person": "3", "number": "sing"},
        "leur": {"role": "object", "person": "3", "number": "plur"},
    },
)

_register_profile(
    "it",
    negations={"non", "mai"},
    question_words={"chi", "cosa", "quando", "dove", "perché", "perche", "come", "quale", "quanto"},
    imperative_markers={"per favore", "per piacere", "esegui", "calcola", "fammi"},
    pronouns={
        "io": {"role": "subject", "person": "1", "number": "sing"},
        "tu": {"role": "subject", "person": "2", "number": "sing"},
        "lui": {"role": "subject", "person": "3", "number": "sing"},
        "lei": {"role": "subject", "person": "3", "number": "sing"},
        "noi": {"role": "subject", "person": "1", "number": "plur"},
        "voi": {"role": "both", "person": "2", "number": "plur"},
        "loro": {"role": "subject", "person": "3", "number": "plur"},
        "mi": {"role": "object", "person": "1", "number": "sing"},
        "ti": {"role": "object", "person": "2", "number": "sing"},
        "gli": {"role": "object", "person": "3", "number": "sing"},
        "le": {"role": "object", "person": "3", "number": "sing"},
        "ci": {"role": "both", "person": "1", "number": "plur"},
        "vi": {"role": "object", "person": "2", "number": "plur"},
        "li": {"role": "object", "person": "3", "number": "plur"},
    },
)


def get_grammar_profile(code: str) -> GrammarProfile:
    normalized = (code or "pt").lower()
    return LANGUAGE_GRAMMAR.get(normalized, LANGUAGE_GRAMMAR["pt"])


__all__ = ["GrammarProfile", "PronounInfo", "get_grammar_profile"]
