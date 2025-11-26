"""High-level façade built on top of the ontology loader."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from .ontology_loader import (
    Concept,
    Ontology,
    DEFAULT_ONTOLOGY_DIR,
    load_ontology,
)


@dataclass
class OntologyIndexConfig:
    ontology_dir: Path = DEFAULT_ONTOLOGY_DIR


class OntologyIndex:
    """Lazy-loading helper that exposes friendly lookup APIs."""

    def __init__(self, config: Optional[OntologyIndexConfig] = None) -> None:
        self.config = config or OntologyIndexConfig()
        self._ontology: Optional[Ontology] = None

    # ----- lazy loading -------------------------------------------------------
    @property
    def ontology(self) -> Ontology:
        if self._ontology is None:
            self._ontology = load_ontology(self.config.ontology_dir)
        return self._ontology

    # ----- public API ---------------------------------------------------------
    def get(self, concept_id: str) -> Optional[Concept]:
        return self.ontology.get_concept(concept_id)

    def by_name(self, name: str) -> Optional[Concept]:
        return self.ontology.find_by_name(name)

    def by_alias(self, alias: str) -> Optional[Concept]:
        return self.ontology.find_by_alias(alias)

    def in_category(self, category_id: str) -> List[Concept]:
        return self.ontology.concepts_in_category(category_id)

    def isa(self, child_id: str, parent_id: str) -> bool:
        return self.ontology.isa(child_id, parent_id)

    def parents_of(self, concept_id: str) -> List[str]:
        return self.ontology.parents_of(concept_id)

    def children_of(self, concept_id: str) -> List[str]:
        return self.ontology.children_of(concept_id)

    def search(self, term: str) -> List[Concept]:
        return self.ontology.search(term)


_global_index: Optional[OntologyIndex] = None


def get_global_index() -> OntologyIndex:
    global _global_index
    if _global_index is None:
        _global_index = OntologyIndex()
    return _global_index
