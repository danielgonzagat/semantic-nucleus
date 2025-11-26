"""Φ-STRUCTURE -> LIU scaffolding."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional

from .semantic_mapper import SemanticParse
from .ontology_index import OntologyIndex, get_global_index


@dataclass
class LIUStructure:
    type: str = "STRUCT"
    fields: Dict[str, str] = field(default_factory=dict)
    confidence: float = 0.0


def phi_structure(parse: SemanticParse, idx: Optional[OntologyIndex] = None) -> LIUStructure:
    if idx is None:
        idx = get_global_index()

    subject = None
    obj = None
    action = None

    for hit in parse.hits:
        if hit.category_id.startswith("A000"):
            subject = hit.token.text
            break

    for hit in reversed(parse.hits):
        if hit.category_id.startswith("A000"):
            obj = hit.token.text
            break

    for hit in parse.hits:
        if hit.category_id.startswith("A003"):
            action = hit.token.text
            break

    fields: Dict[str, str] = {}
    if subject:
        fields["subject"] = subject
    if action:
        fields["action"] = action
    if obj and obj != subject:
        fields["object"] = obj

    confidence = 0.5
    if subject and action and obj:
        confidence = 0.92
    elif subject and action:
        confidence = 0.8

    return LIUStructure(fields=fields, confidence=confidence)
