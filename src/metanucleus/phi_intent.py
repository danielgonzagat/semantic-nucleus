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
    text_lower = parse.text.lower()
    scores: Dict[str, float] = {
        "statement": 0.2,
        "question": 0.0,
        "definition_request": 0.0,
        "command": 0.0,
        "greeting": 0.0,
    }
    reason_map: Dict[str, List[str]] = {label: [] for label in scores}

    def add(label: str, value: float, note: str) -> None:
        scores[label] = scores.get(label, 0.0) + value
        reason_map.setdefault(label, []).append(note)

    if any(token.lower in patterns.get("greeting", []) for token in parse.tokens if not token.is_punctuation):
        add("greeting", 1.5, "match greeting token")

    for pat in patterns.get("definition_request", []):
        if pat in text_lower:
            add("definition_request", 1.2, f"match definition_request: {pat!r}")

    if any(token.text == "?" for token in parse.tokens) or text_lower.strip().endswith("?"):
        add("question", 1.5, "termina_com_?")

    # Imperative heuristic (first token verb-like or operator concept)
    tokens_lower = [t.lower for t in parse.tokens if not t.is_punctuation]
    if tokens_lower:
        first = tokens_lower[0]
        if first.endswith(("ar", "er", "ir")):
            add("command", 0.8, "primeiro token parece verbo")
        concept = idx.by_name(first) or idx.by_alias(first)
        if concept and concept.category_id.startswith("A003"):
            add("command", 1.0, "primeiro token é operador")

    # If we matched a definition request but it's also clearly a question, bump question score
    if scores["definition_request"] > 0 and scores["question"] > 0:
        add("question", 0.5, "definition_request também marcado como pergunta")

    label = max(scores.items(), key=lambda item: item[1])[0]
    top_score = scores[label]
    reasons = reason_map.get(label, [])
    if not reasons:
        reasons.append("padrão neutro; assumindo 'statement'")
    confidence = min(0.95, 0.4 + top_score / 2)
    return IntentFrame(label=label, confidence=confidence, reasons=reasons)
