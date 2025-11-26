"""
LxU + PSE — lexicalizador e parser estrutural determinístico.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum, auto
from typing import Dict, List, Optional

from metanucleus.core.liu import Node, struct, text

TOKEN_PATTERN = re.compile(r"[A-Za-zÀ-ÿ0-9]+|[^\w\s]", re.UNICODE)


@dataclass()
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

GREET_PT = {"oi", "olá", "ola", "opa", "eae", "eaí", "bom dia", "boa tarde", "boa noite"}
GREET_EN = {"hi", "hello", "hey", "yo"}

CMD_MARKERS_PT = {"faça", "faz", "cria", "gera", "mostra", "executa", "roda", "abre", "fecha", "lista"}
CMD_MARKERS_EN = {"do", "make", "create", "generate", "show", "run", "open", "close", "list"}

QWORDS_PT = {"o que", "que", "quando", "onde", "por que", "porque", "qual", "quais", "como"}
QWORDS_EN = {"what", "when", "where", "why", "how", "which"}


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


def detect_language(text_raw: str, tokens: List[Token]) -> str:
    lowered = text_raw.lower()
    if any(ch in lowered for ch in "ãõáéíóúâêôç"):
        return "pt"
    lowers = {tok.lower for tok in tokens}
    if lowers & {"the", "this", "that"}:
        return "en"
    if lowers & {"vc", "você", "voce", "pra", "tá", "ta"}:
        return "pt"
    if any(tok.lower in GREET_PT for tok in tokens):
        return "pt"
    if any(tok.lower in GREET_EN for tok in tokens):
        return "en"
    return "pt"


def detect_intent(text_raw: str, tokens: List[Token], lang: str) -> UtteranceIntent:
    stripped = text_raw.strip()
    lowers = [tok.lower for tok in tokens]
    joined = " ".join(lowers)

    if "?" in stripped:
        return UtteranceIntent.QUESTION
    if lang == "pt":
        if any(marker in joined for marker in GREET_PT):
            return UtteranceIntent.GREETING
    else:
        if any(marker in joined for marker in GREET_EN):
            return UtteranceIntent.GREETING
    qwords = QWORDS_PT if lang == "pt" else QWORDS_EN
    if any(q in joined for q in qwords):
        return UtteranceIntent.QUESTION
    cmd_markers = CMD_MARKERS_PT if lang == "pt" else CMD_MARKERS_EN
    if lowers and (lowers[0] in cmd_markers or tokens[0].tag == "VERB"):
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
    lang = detect_language(text_raw, tokens)
    intent = detect_intent(text_raw, tokens, lang)

    subject = _select_subject(tokens)
    verb = _select_verb(tokens)
    obj = _object_fragment(tokens, verb)

    fields: Dict[str, Node] = {
        "kind": text("utterance"),
        "lang": text(lang),
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
