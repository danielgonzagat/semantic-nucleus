"""
Logic-Engine – inferência proposicional determinística (modus ponens e modus tollens).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, List, Set, Tuple
import unicodedata


def normalize_statement(text: str) -> str:
    stripped = _strip_accents(text)
    normalized = " ".join(stripped.strip().upper().split())
    return normalized


def negate(statement: str) -> str:
    statement = normalize_statement(statement)
    if statement.startswith("NOT "):
        return statement[4:]
    return f"NOT {statement}"


def _strip_accents(value: str) -> str:
    decomposed = unicodedata.normalize("NFD", value)
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


@dataclass(frozen=True)
class LogicRule:
    premises: Tuple[str, ...]
    conclusion: str

    @classmethod
    def from_strings(cls, premises: Iterable[str], conclusion: str) -> "LogicRule":
        normalized_premises = tuple(normalize_statement(p) for p in premises)
        normalized_conclusion = normalize_statement(conclusion)
        if not normalized_premises:
            raise ValueError("LogicRule requires at least one premise.")
        return cls(premises=normalized_premises, conclusion=normalized_conclusion)


@dataclass
class LogicEngine:
    facts: dict[str, bool] = field(default_factory=dict)
    rules: List[LogicRule] = field(default_factory=list)
    derived_order: List[str] = field(default_factory=list)

    def add_fact(self, statement: str, truth: bool = True) -> None:
        key = normalize_statement(statement)
        value = bool(truth)
        if key in self.facts:
            if self.facts[key] != value:
                raise ValueError(f"Contradictory fact detected for '{key}'.")
            return
        negated = negate(key)
        if negated in self.facts and self.facts[negated] == value:
            raise ValueError(f"Contradictory fact detected between '{key}' and '{negated}'.")
        self.facts[key] = value
        if key not in self.derived_order:
            self.derived_order.append(key)

    def add_rule(self, premises: Iterable[str], conclusion: str) -> LogicRule:
        rule = LogicRule.from_strings(premises, conclusion)
        self.rules.append(rule)
        return rule

    def infer(self, max_iterations: int | None = None) -> Set[str]:
        iterations = 0
        new_facts: Set[str] = set()
        while True:
            if max_iterations is not None and iterations >= max_iterations:
                break
            iterations += 1
            produced = False
            for rule in self.rules:
                if self._apply_modus_ponens(rule, new_facts):
                    produced = True
                if self._apply_modus_tollens(rule, new_facts):
                    produced = True
            if not produced:
                break
        return new_facts

    def _apply_modus_ponens(self, rule: LogicRule, new_facts: Set[str]) -> bool:
        if all(self.facts.get(premise) for premise in rule.premises):
            conclusion_key = rule.conclusion
            if conclusion_key not in self.facts:
                self.add_fact(conclusion_key, True)
                new_facts.add(conclusion_key)
                return True
        return False

    def _apply_modus_tollens(self, rule: LogicRule, new_facts: Set[str]) -> bool:
        if len(rule.premises) != 1:
            return False
        premise = rule.premises[0]
        conclusion_negated = negate(rule.conclusion)
        if self.facts.get(conclusion_negated):
            negated_premise = negate(premise)
            if negated_premise not in self.facts:
                self.add_fact(negated_premise, True)
                new_facts.add(negated_premise)
                return True
        return False


__all__ = ["LogicEngine", "LogicRule", "normalize_statement", "negate"]
