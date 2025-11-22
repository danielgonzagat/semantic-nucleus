"""
LxU + PSE — lexicalizador e parser estrutural determinístico.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum, auto
from typing import Dict, List, Optional

from metanucleus.core.liu import Node, struct, text
from metanucleus.core.lang_profiles import (
    LanguageCode,
    LanguageFeatures,
    extract_language_features,
)

TOKEN_PATTERN = re.compile(r"[A-Za-zÀ-ÿ0-9]+|[^\w\s]", re.UNICODE)


@dataclass(slots=True)
class Token:
    surface: str
    lower: str
    tag: str


class UtteranceIntent(str, Enum):
    GREETING = "greeting"
    QUESTION = "question"
    COMMAND = "command"
    STATEMENT = "statement"


PRONOUNS_PT = {"eu", "tu", "ele", "ela", "nos", "nós", "voce", "você", "vocês", "eles", "elas"}
PRONOUNS_EN = {"i", "you", "he", "she", "we", "they"}

VERBS_PT = {
    "ser",
    "estar",
    "fazer",
    "criar",
    "gerar",
    "mostrar",
    "rodar",
    "executar",
    "abrir",
    "fechar",
    "pensar",
    "responder",
    "ajudar",
    "explicar",
    "dizer",
    "perguntar",
    "querer",
}
VERBS_EN = {
    "be",
    "do",
    "make",
    "create",
    "generate",
    "show",
    "run",
    "open",
    "close",
    "think",
    "answer",
    "help",
    "explain",
    "say",
    "ask",
    "want",
}

QUESTION_WORDS = {
    "pt": {"o que", "que", "quando", "onde", "por que", "porque", "qual", "quais", "como"},
    "en": {"what", "when", "where", "why", "how", "which"},
    "es": {"qué", "que", "cuando", "donde", "cómo", "como", "por qué", "porque"},
    "fr": {"pourquoi", "comment", "quand", "où", "qui"},
    "it": {"perché", "perche", "come", "quando", "dove", "chi"},
    "de": {"warum", "wie", "wann", "wo", "wer"},
}

COMMAND_MARKERS = {
    "pt": {"faça", "faz", "cria", "gera", "mostra", "executa", "roda", "abre", "fecha", "lista"},
    "en": {"do", "make", "create", "generate", "show", "run", "open", "close", "list", "reset"},
    "es": {"haz", "hacer", "ejecuta", "lista", "muestra"},
    "fr": {"fais", "faire", "montre", "liste"},
    "it": {"esegui", "fai", "crea", "mostra", "lista"},
    "de": {"mach", "ausführen", "liste", "zeige"},
}


def lex(text_raw: str) -> List[Token]:
    tokens: List[Token] = []
    for match in TOKEN_PATTERN.finditer(text_raw):
        surface = match.group(0)
        lower = surface.lower()
        if surface.isdigit():
            tag = "NUMBER"
        elif re.fullmatch(r"[^\w\s]", surface):
            tag = "PUNCT"
        elif lower in PRONOUNS_PT or lower in PRONOUNS_EN:
            tag = "PRON"
        elif lower in VERBS_PT or lower in VERBS_EN:
            tag = "VERB"
        else:
            tag = "WORD"
        tokens.append(Token(surface=surface, lower=lower, tag=tag))
    return tokens


def _intent_from_features(
    text_raw: str,
    tokens: List[Token],
    features: LanguageFeatures,
    lang: str,
) -> UtteranceIntent:
    lowered = text_raw.lower()
    joined = " ".join(tok.lower for tok in tokens)

    if features.is_greeting_like:
        return UtteranceIntent.GREETING
    if features.has_question_mark:
        return UtteranceIntent.QUESTION

    qwords = QUESTION_WORDS.get(lang, QUESTION_WORDS["en"])
    if any(q in joined for q in qwords):
        return UtteranceIntent.QUESTION

    cmd_markers = COMMAND_MARKERS.get(lang, COMMAND_MARKERS["en"])
    if tokens:
        first = tokens[0]
        if first.tag == "VERB" or first.lower in cmd_markers or joined.startswith(tuple(cmd_markers)):
            return UtteranceIntent.COMMAND

    if any(marker in lowered for marker in cmd_markers):
        return UtteranceIntent.COMMAND

    return UtteranceIntent.STATEMENT


def _token_struct(tokens: List[Token]) -> Node:
    fields: Dict[str, Node] = {}
    for idx, tok in enumerate(tokens):
        fields[f"t{idx}"] = struct(
            kind=text("token"),
            surface=text(tok.surface),
            lower=text(tok.lower),
            tag=text(tok.tag),
        )
    return struct(**fields)


def _select_subject(tokens: List[Token]) -> Optional[str]:
    for tok in tokens:
        if tok.tag == "PRON":
            return tok.surface
    for tok in tokens:
        if tok.tag in {"WORD", "NUMBER"}:
            return tok.surface
    return None


def _select_verb(tokens: List[Token]) -> Optional[str]:
    for tok in tokens:
        if tok.tag == "VERB":
            return tok.surface
    if len(tokens) >= 2:
        return tokens[1].surface
    return None


def _object_fragment(tokens: List[Token], verb_surface: Optional[str]) -> str:
    if not verb_surface:
        return ""
    try:
        verb_index = next(i for i, tok in enumerate(tokens) if tok.surface == verb_surface)
    except StopIteration:
        return ""
    frag = " ".join(tok.surface for tok in tokens[verb_index + 1 :] if tok.tag != "PUNCT")
    return frag.strip()


def parse_utterance(text_raw: str) -> Node:
    tokens = lex(text_raw)
    features = extract_language_features(text_raw)
    lang = features.lang if features.lang != LanguageCode.UNKNOWN.value else LanguageCode.PT.value
    intent = _intent_from_features(text_raw, tokens, features, lang)

    subject = _select_subject(tokens)
    verb = _select_verb(tokens)
    obj = _object_fragment(tokens, verb)

    fields: Dict[str, Node] = {
        "kind": text("utterance"),
        "lang": text(lang),
        "lang_confidence": text(f"{features.confidence:.3f}"),
        "raw": text(text_raw),
        "content": text(text_raw),
        "intent": text(intent.value),
        "tokens": _token_struct(tokens),
        "length": text(str(len(tokens))),
    }

    if subject:
        fields["subject"] = text(subject)
    if verb:
        fields["verb"] = text(verb)
    if obj:
        fields["object"] = text(obj)

    return struct(**fields)
