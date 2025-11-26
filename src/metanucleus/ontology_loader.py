"""Utilities to load ontology JSON modules into in-memory structures."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional
import json

# Path assumes the repository layout where this module lives in src/metanucleus/
DEFAULT_ONTOLOGY_DIR = Path(__file__).resolve().parent.parent / "ontology"


@dataclass
class Concept:
    id: str
    name: str
    aliases: List[str] = field(default_factory=list)
    isa: List[str] = field(default_factory=list)
    examples_pt: List[str] = field(default_factory=list)
    examples_en: List[str] = field(default_factory=list)
    category_id: str = ""


@dataclass
class Category:
    id: str
    name: str
    concepts: List[Concept] = field(default_factory=list)


@dataclass
class Module:
    module: str
    range: str
    name: str
    categories: List[Category] = field(default_factory=list)


class Ontology:
    """Main ontology container with helper lookup structures."""

    def __init__(self) -> None:
        self.modules: Dict[str, Module] = {}
        self.categories: Dict[str, Category] = {}
        self.concepts_by_id: Dict[str, Concept] = {}
        self.concepts_by_name: Dict[str, Concept] = {}
        self.concepts_by_alias: Dict[str, Concept] = {}
        self.category_members: Dict[str, List[str]] = {}
        self.isa_graph: Dict[str, List[str]] = {}
        self.reverse_isa_graph: Dict[str, List[str]] = {}

    # ----- public query helpers -------------------------------------------------
    def get_concept(self, concept_id: str) -> Optional[Concept]:
        return self.concepts_by_id.get(concept_id)

    def find_by_name(self, name: str) -> Optional[Concept]:
        return self.concepts_by_name.get(name)

    def find_by_alias(self, alias: str) -> Optional[Concept]:
        return self.concepts_by_alias.get(alias)

    def concepts_in_category(self, category_id: str) -> List[Concept]:
        ids = self.category_members.get(category_id, [])
        return [self.concepts_by_id[cid] for cid in ids if cid in self.concepts_by_id]

    def isa(self, child_id: str, parent_id: str) -> bool:
        """Returns True if child_id is a descendant of parent_id."""
        visited = set()
        stack = [child_id]
        while stack:
            current = stack.pop()
            if current == parent_id:
                return True
            if current in visited:
                continue
            visited.add(current)
            stack.extend(self.isa_graph.get(current, []))
        return False

    def parents_of(self, concept_id: str) -> List[str]:
        return list(self.isa_graph.get(concept_id, []))

    def children_of(self, concept_id: str) -> List[str]:
        return list(self.reverse_isa_graph.get(concept_id, []))

    def search(self, term: str) -> List[Concept]:
        term_lower = term.lower()
        results: List[Concept] = []
        for concept in self.concepts_by_id.values():
            if term_lower in concept.name.lower():
                results.append(concept)
                continue
            if any(term_lower in alias.lower() for alias in concept.aliases):
                results.append(concept)
        return results


# ----- internal helpers --------------------------------------------------------


def _load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _load_module_from_file(path: Path) -> Module:
    data = _load_json(path)
    module_id = data.get("module", data.get("module_id", ""))
    module = Module(
        module=module_id,
        range=data.get("range", ""),
        name=data.get("name", ""),
        categories=[],
    )

    for category_data in data.get("categories", []):
        category = Category(
            id=category_data["id"],
            name=category_data["name"],
            concepts=[],
        )
        for concept_data in category_data.get("concepts", []):
            concept = Concept(
                id=concept_data["id"],
                name=concept_data["name"],
                aliases=list(concept_data.get("aliases", [])),
                isa=list(concept_data.get("isa", [])),
                examples_pt=list(concept_data.get("examples", {}).get("pt", [])),
                examples_en=list(concept_data.get("examples", {}).get("en", [])),
                category_id=category.id,
            )
            category.concepts.append(concept)
        module.categories.append(category)

    return module


def load_ontology(
    ontology_dir: Optional[Path] = None,
    extra_files: Optional[Iterable[Path]] = None,
) -> Ontology:
    """Load ontology modules from JSON files into an Ontology object."""

    if ontology_dir is None:
        ontology_dir = DEFAULT_ONTOLOGY_DIR

    ontology = Ontology()
    core_files = sorted(ontology_dir.glob("core_*.json"))
    extra = list(extra_files or [])

    for path in core_files + extra:
        module = _load_module_from_file(path)
        ontology.modules[module.name] = module
        for category in module.categories:
            ontology.categories[category.id] = category
            member_ids: List[str] = []
            for concept in category.concepts:
                ontology.concepts_by_id[concept.id] = concept
                ontology.concepts_by_name.setdefault(concept.name, concept)
                for alias in concept.aliases:
                    ontology.concepts_by_alias.setdefault(alias, concept)
                member_ids.append(concept.id)
                ontology.isa_graph.setdefault(concept.id, [])
                for parent in concept.isa:
                    ontology.isa_graph[concept.id].append(parent)
                    ontology.reverse_isa_graph.setdefault(parent, []).append(concept.id)
            ontology.category_members[category.id] = member_ids

    return ontology
