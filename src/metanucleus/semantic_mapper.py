"""LxU + Parser Semântico Estrutural mínimo."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Optional

from .ontology_index import OntologyIndex, get_global_index, Concept


@dataclass
class SemanticToken:
    text: str
    lemma: str
    lower: str
    is_punctuation: bool = False
    is_number: bool = False


@dataclass
class SemanticHit:
    token_index: int
    token: SemanticToken
    concept_id: str
    concept_name: str
    category_id: str


@dataclass
class IntentGuess:
    label: str
    confidence: float
    reasons: List[str] = field(default_factory=list)


@dataclass
class SemanticParse:
    text: str
    tokens: List[SemanticToken]
    hits: List[SemanticHit]
    intent: IntentGuess
    extra: dict[str, Any] = field(default_factory=dict)


_PUNCT = {".", ",", "?", "!", ";", ":", "…"}


def _tokenize(text: str) -> List[SemanticToken]:
    raw: List[str] = []
    buf = ""
    for ch in text:
        if ch.isspace():
            if buf:
                raw.append(buf)
                buf = ""
            continue
        if ch in _PUNCT:
            if buf:
                raw.append(buf)
                buf = ""
            raw.append(ch)
        else:
            buf += ch
    if buf:
        raw.append(buf)

    tokens: List[SemanticToken] = []
    for item in raw:
        lower = item.lower()
        is_punct = item in _PUNCT
        is_number = lower.replace(",", "").replace(".", "").isdigit()
        tokens.append(
            SemanticToken(
                text=item,
                lemma=lower,
                lower=lower,
                is_punctuation=is_punct,
                is_number=is_number,
            )
        )
    return tokens


def _guess_intent(tokens: List[SemanticToken]) -> IntentGuess:
    reasons: List[str] = []
    if any(t.text == "?" for t in tokens):
        reasons.append("presença de '?'")
        return IntentGuess(label="question", confidence=0.9, reasons=reasons)

    greetings = {"oi", "olá", "ola", "hello", "hi", "bom dia", "boa tarde", "boa noite"}
    if any(t.lower in greetings for t in tokens if not t.is_punctuation):
        reasons.append("token em conjunto de saudação")
        return IntentGuess(label="greeting", confidence=0.85, reasons=reasons)

    if tokens:
        first = tokens[0].lower
        if first.endswith("ar") or first.endswith("er") or first.endswith("ir"):
            reasons.append("primeiro token parece verbo")
            return IntentGuess(label="command", confidence=0.6, reasons=reasons)

    reasons.append("sem marcador forte; assumindo 'statement'")
    return IntentGuess(label="statement", confidence=0.5, reasons=reasons)


def _map_tokens_to_concepts(tokens: List[SemanticToken], idx: OntologyIndex) -> List[SemanticHit]:
    hits: List[SemanticHit] = []
    for i, token in enumerate(tokens):
        if token.is_punctuation or token.is_number:
            continue
        concept: Optional[Concept] = idx.by_name(token.lower)
        if concept is None:
            concept = idx.by_alias(token.lower)
        if concept is not None:
            hits.append(
                SemanticHit(
                    token_index=i,
                    token=token,
                    concept_id=concept.id,
                    concept_name=concept.name,
                    category_id=concept.category_id,
                )
            )
    return hits


def analyze_text(text: str, index: Optional[OntologyIndex] = None) -> SemanticParse:
    if index is None:
        index = get_global_index()

    tokens = _tokenize(text)
    intent = _guess_intent(tokens)
    hits = _map_tokens_to_concepts(tokens, index)
    extra = {
        "num_tokens": len(tokens),
        "num_hits": len(hits),
    }

    return SemanticParse(text=text, tokens=tokens, hits=hits, intent=intent, extra=extra)
