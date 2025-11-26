"""
Knowledge Graph (Triplestore) Implementation.
Stores facts as symbolic structures and supports unification-based querying.
This replaces the simple list-based memory.
"""

from typing import List, Iterator, Optional, Any, Dict
from metanucleus.core_unification import Structure, Variable, Term, unify, substitute, is_variable

class KnowledgeGraph:
    def __init__(self):
        # In-memory storage of facts (Structures)
        # In a production system, this would be an indexed database (e.g., B-Tree)
        self.facts: List[Structure] = []

    def add(self, fact: Structure) -> None:
        """Add a fact to the graph if it doesn't exist."""
        # Naive check for duplicates (O(N)) - acceptable for this scale
        if fact not in self.facts:
            self.facts.append(fact)

    def remove(self, fact: Structure) -> None:
        if fact in self.facts:
            self.facts.remove(fact)

    def query(self, pattern: Structure) -> Iterator[Dict[Variable, Term]]:
        """
        Find all facts that match the pattern.
        Returns an iterator of substitutions (bindings).
        """
        for fact in self.facts:
            subst = unify(pattern, fact, {})
            if subst is not None:
                yield subst

    def dump(self) -> List[str]:
        return [str(f) for f in self.facts]

    def load_bulk(self, facts: List[Structure]) -> None:
        for f in facts:
            self.add(f)

# Global instance for the session
_GLOBAL_KB = KnowledgeGraph()

def get_kb() -> KnowledgeGraph:
    return _GLOBAL_KB
