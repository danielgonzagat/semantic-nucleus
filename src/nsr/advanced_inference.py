"""
Real Inference Engine - Powered by Unification.
Replaces the fake heuristics with a rigorous Forward Chaining logic engine (GOFAI).

Capabilities:
- Applies rules recursively to derive new facts.
- Uses the 'core_unification' engine for variable binding.
- Supports transitive, causal, and conditional logic strictly.
"""

from __future__ import annotations
from typing import List, Set, Iterator, Tuple, Any

# Import our new rigorous math core
from metanucleus.core_unification import (
    unify, substitute, Variable, Structure, Term, var, struct, sym, is_compound
)

@dataclass
class InferenceRule:
    """A logical implication: IF premises THEN conclusion."""
    name: str
    premises: List[Structure]
    conclusion: Structure
    
    def __repr__(self):
        prem_str = " ^ ".join(str(p) for p in self.premises)
        return f"{self.name}: {prem_str} => {self.conclusion}"

from dataclasses import dataclass, field

class ForwardChainingEngine:
    """
    A deterministic inference engine.
    
    Algorithm:
    1. Matches rule premises against known facts using Unification.
    2. Binds variables (e.g., ?x -> 'rain').
    3. Instantiates conclusions (e.g., wet('rain')).
    4. Adds new facts to the Knowledge Base.
    5. Repeats until a fixed point is reached (no new facts).
    """
    
    def __init__(self):
        self.facts: List[Structure] = []
        self.rules: List[InferenceRule] = []
        # To prevent cycles and redundant work
        self._fact_hashes: Set[str] = set() 
        self.derivations: List[str] = []

    def add_fact(self, fact: Structure):
        """Add a fact if it's new."""
        h = str(fact)
        if h not in self._fact_hashes:
            self.facts.append(fact)
            self._fact_hashes.add(h)
            return True
        return False

    def add_rule(self, name: str, premises: List[Structure], conclusion: Structure):
        """Register a logic rule."""
        self.rules.append(InferenceRule(name, premises, conclusion))

    def _find_matches(self, goals: List[Structure], subst: dict) -> Iterator[dict]:
        """
        Recursive backtracking search to find all ways to satisfy a list of goals (premises).
        This is essentially a Prolog query engine.
        """
        if not goals:
            yield subst
            return

        first_goal = goals[0]
        remaining_goals = goals[1:]

        # We need to instantiate the goal with current substitution so far
        # e.g., if ?x=rain, and goal is wet(?x), we look for wet(rain)
        current_goal_term = substitute(first_goal, subst)

        for fact in self.facts:
            # Try to unify the current goal with a known fact
            new_subst = unify(current_goal_term, fact, subst)
            if new_subst is not None:
                # If it matches, try to solve the rest of the goals with the new substitution
                yield from self._find_matches(remaining_goals, new_subst)

    def step(self) -> int:
        """
        Run one pass of inference over all rules.
        Returns number of new facts derived.
        """
        new_facts_count = 0
        
        for rule in self.rules:
            # Find all valid substitutions for this rule's premises
            for valid_subst in self._find_matches(rule.premises, {}):
                # Generate the conclusion based on the match
                new_fact = substitute(rule.conclusion, valid_subst)
                
                # If it's a valid structure and we haven't seen it...
                if isinstance(new_fact, Structure) and self.add_fact(new_fact):
                    new_facts_count += 1
                    # Log the derivation proof
                    proof = f"Derived {new_fact} via [{rule.name}] using {valid_subst}"
                    self.derivations.append(proof)
        
        return new_facts_count

    def run_until_fixpoint(self, max_steps=50) -> List[str]:
        """Run inference until no new facts can be derived."""
        total_derived = 0
        for i in range(max_steps):
            count = self.step()
            if count == 0:
                break
            total_derived += count
        return self.derivations

# --- Convenience Factory ---

def create_standard_engine() -> ForwardChainingEngine:
    """Creates an engine with standard logical laws."""
    engine = ForwardChainingEngine()
    
    # Variables
    x, y, z = var("x"), var("y"), var("z")
    
    # Rule: Causal Transitivity
    # causes(?x, ?y) ^ causes(?y, ?z) => causes(?x, ?z)
    engine.add_rule(
        "causal_transitivity",
        [struct("causes", x, y), struct("causes", y, z)],
        struct("causes", x, z)
    )
    
    # Rule: Modus Ponens (generalized for properties)
    # implies(?x, ?y) ^ is(?x) => is(?y)
    # Note: simplified representation for this demo
    engine.add_rule(
        "modus_ponens",
        [struct("implies", x, y), struct("true", x)],
        struct("true", y)
    )

    # Rule: Temporal Ordering
    # before(?x, ?y) ^ before(?y, ?z) => before(?x, ?z)
    engine.add_rule(
        "temporal_transitivity",
        [struct("before", x, y), struct("before", y, z)],
        struct("before", x, z)
    )
    
    return engine