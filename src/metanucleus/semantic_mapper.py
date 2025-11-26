"""LxU + Parser Semântico Estrutural mínimo."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Optional, Sequence
import unicodedata

from .ontology_index import OntologyIndex, get_global_index, Concept


@dataclass
class SemanticToken:
    text: str
    lemma: str
    lower: str
    norm: str
    is_punctuation: bool = False
    is_number: bool = False


@dataclass
class SemanticHit:
    token_index: int
    token: SemanticToken
    concept_id: str
    concept_name: str
    category_id: str
    surface: str


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
                norm=_strip_accents(lower),
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
    used_indices: set[int] = set()

    def _record(indices: Sequence[int], concept: Concept, surface: str) -> None:
        hits.append(
            SemanticHit(
                token_index=indices[0],
                token=tokens[indices[0]],
                concept_id=concept.id,
                concept_name=concept.name,
                category_id=concept.category_id,
                surface=surface,
            )
        )
        used_indices.update(indices)

    non_punct = [i for i, tok in enumerate(tokens) if not tok.is_punctuation]
    for start in range(len(non_punct)):
        if non_punct[start] in used_indices:
            continue
        for span_len in (3, 2):
            if start + span_len > len(non_punct):
                continue
            indices = non_punct[start : start + span_len]
            if any(idx in used_indices for idx in indices):
                continue
            surface = " ".join(tokens[idx].text for idx in indices)
            concept = _lookup_phrase(surface, idx)
            if concept:
                _record(indices, concept, surface)
                break

    for i, token in enumerate(tokens):
        if i in used_indices or token.is_punctuation or token.is_number:
            continue
        concept = _lookup_phrase(token.text, idx)
        if concept is None and "_" in token.text:
            concept = _lookup_phrase(token.text.replace("_", " "), idx)
        if concept is None and token.norm != token.lower:
            concept = _lookup_phrase(token.norm, idx)
        if concept:
            _record([i], concept, token.text)

    return hits


def _lookup_phrase(surface: str, idx: OntologyIndex) -> Optional[Concept]:
    for candidate in _phrase_candidates(surface):
        concept = idx.by_name(candidate)
        if concept:
            return concept
        concept = idx.by_alias(candidate)
        if concept:
            return concept
    return None


def _phrase_candidates(surface: str) -> List[str]:
    raw = surface.strip().lower()
    normalized_space = " ".join(raw.replace("_", " ").split())
    variants = {
        normalized_space,
        normalized_space.replace(" ", "_"),
        normalized_space.replace("-", " "),
    }
    stripped = _strip_accents(normalized_space)
    variants.add(stripped)
    variants.add(stripped.replace(" ", "_"))
    return [variant for variant in variants if variant]


def _strip_accents(text: str) -> str:
    return "".join(ch for ch in unicodedata.normalize("NFD", text) if unicodedata.category(ch) != "Mn")


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
