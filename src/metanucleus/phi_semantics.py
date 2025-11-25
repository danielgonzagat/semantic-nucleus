"""Φ-SEMANTICS v1."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .semantic_mapper import SemanticParse
from .ontology_index import OntologyIndex, get_global_index


@dataclass
class SemanticFrame:
    label: str
    confidence: float
    roles: Dict[str, List[str]] = field(default_factory=dict)
    signals: List[str] = field(default_factory=list)


def phi_semantics(parse: SemanticParse, idx: Optional[OntologyIndex] = None) -> SemanticFrame:
    if idx is None:
        idx = get_global_index()

    signals: List[str] = []
    hits = parse.hits

    if any(hit.category_id.startswith("A000") for hit in hits):
        signals.append("menção_de_entidade")
    if any(hit.category_id.startswith("A001") for hit in hits):
        signals.append("menção_de_estrutura")
    if any(hit.category_id.startswith("A003") for hit in hits):
        signals.append("menção_de_operador")
    if any(hit.concept_id == "A005-002" for hit in hits):
        signals.append("relação_causal")

    has_entity = any(hit.category_id == "A000" for hit in hits)
    has_property = any(hit.category_id == "A006" for hit in hits)
    if has_entity and has_property:
        return SemanticFrame(
            label="description",
            confidence=0.75,
            roles={"entities": [hit.concept_id for hit in hits]},
            signals=signals + ["descrição_detectada"],
        )

    if any(hit.category_id.startswith("A005") for hit in hits):
        relations = [hit.concept_id for hit in hits if hit.category_id.startswith("A005")]
        return SemanticFrame(
            label="relation_statement",
            confidence=0.8,
            roles={"relations": relations},
            signals=signals + ["relação_detectada"],
        )

    return SemanticFrame(label="semantic_statement", confidence=0.5, roles={}, signals=signals or ["neutro"])
