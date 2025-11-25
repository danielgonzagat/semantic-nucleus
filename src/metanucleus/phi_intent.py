"""Φ-INTENT v1.1 built on config patterns."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional
import json

from .semantic_mapper import SemanticParse
from .ontology_index import OntologyIndex, get_global_index

INTENT_CONFIG_PATH = Path(__file__).resolve().parent / "config" / "intent_patterns.json"


@dataclass
class IntentFrame:
    label: str
    confidence: float
    reasons: List[str] = field(default_factory=list)


def _load_intent_patterns(path: Path = INTENT_CONFIG_PATH) -> Dict[str, List[str]]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    patterns: Dict[str, List[str]] = {}
    for key, values in data.items():
        patterns[key] = [str(value).lower() for value in values]
    return patterns


def phi_intent(parse: SemanticParse, idx: Optional[OntologyIndex] = None) -> IntentFrame:
    if idx is None:
        idx = get_global_index()

    patterns = _load_intent_patterns()
    reasons: List[str] = []
    text_lower = parse.text.lower()

    for pat in patterns.get("greeting", []):
        if pat in text_lower:
            reasons.append(f"match greeting: {pat!r}")
            return IntentFrame(label="greeting", confidence=0.9, reasons=reasons)

    for pat in patterns.get("definition_request", []):
        if pat in text_lower:
            reasons.append(f"match definition_request: {pat!r}")
            return IntentFrame(label="definition_request", confidence=0.9, reasons=reasons)

    if any(token.text == "?" for token in parse.tokens):
        reasons.append("termina_com_?")
        return IntentFrame(label="question", confidence=0.9, reasons=reasons)

    tokens_lower = [t.lower for t in parse.tokens if not t.is_punctuation]
    if tokens_lower:
        first = tokens_lower[0]
        concept = idx.by_name(first) or idx.by_alias(first)
        if concept and concept.category_id.startswith("A003"):
            reasons.append("primeiro_token_é_operador")
            return IntentFrame(label="command", confidence=0.7, reasons=reasons)

    reasons.append("padrão neutro; assumindo 'statement'")
    return IntentFrame(label="statement", confidence=0.5, reasons=reasons)
