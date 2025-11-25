"""
Meta-Learning: Indução de regras determinísticas a partir de padrões de execução bem-sucedidos.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, replace
from typing import Dict, Iterable, List, Tuple

from liu import (
    Node,
    NodeKind,
    struct,
    fingerprint,
    relation,
    var,
)
from nsr.state import Rule


@dataclass(frozen=True)
class LearnedPattern:
    antecedents: Tuple[Node, ...]
    consequent: Node
    confidence: float
    evidence_count: int
    promoted: bool = False


class MetaLearningEngine:
    """
    Motor de aprendizado que observa resoluções de problemas e tenta generalizar regras.

    A abordagem atual coleta evidências determinísticas sobre dois padrões clássicos:
    - Transitividade: se R(a,b) e R(b,c) aparecem frequentemente, sugerimos R(a,c).
    - Simetria: se R(a,b) e R(b,a) coocorrem, sugerimos simetria para R.
    """

    MIN_EVIDENCE = 2

    def __init__(self) -> None:
        self.potential_rules: Dict[Tuple[str, str], LearnedPattern] = {}

    def learn_from_trace(self, trace_summary: Node, context: Tuple[Node, ...]) -> List[Rule]:
        relations = _gather_relations(context)
        if not relations:
            return []
        suggestions: List[Rule] = []
        suggestions.extend(self._harvest_transitivity(relations))
        suggestions.extend(self._harvest_symmetry(relations))
        return suggestions

    def _harvest_transitivity(self, relations: List[Node]) -> List[Rule]:
        evidence_by_label = _transitive_evidence(relations)
        rules: List[Rule] = []
        for label, evidence in evidence_by_label.items():
            if evidence <= 0:
                continue
            antecedents = (
                relation(label, var("?x"), var("?y")),
                relation(label, var("?y"), var("?z")),
            )
            consequent = relation(label, var("?x"), var("?z"))
            rules.extend(
                self._register_pattern(
                    key=("transitive", label),
                    antecedents=antecedents,
                    consequent=consequent,
                    evidence=evidence,
                )
            )
        return rules

    def _harvest_symmetry(self, relations: List[Node]) -> List[Rule]:
        evidence_by_label = _symmetric_evidence(relations)
        rules: List[Rule] = []
        for label, evidence in evidence_by_label.items():
            if evidence <= 0:
                continue
            antecedents = (relation(label, var("?x"), var("?y")),)
            consequent = relation(label, var("?y"), var("?x"))
            rules.extend(
                self._register_pattern(
                    key=("symmetric", label),
                    antecedents=antecedents,
                    consequent=consequent,
                    evidence=evidence,
                )
            )
        return rules

    def _register_pattern(
        self,
        *,
        key: Tuple[str, str],
        antecedents: Tuple[Node, ...],
        consequent: Node,
        evidence: int,
    ) -> List[Rule]:
        existing = self.potential_rules.get(key)
        if existing is None:
            pattern = LearnedPattern(
                antecedents=antecedents,
                consequent=consequent,
                confidence=_confidence(evidence),
                evidence_count=evidence,
            )
        else:
            if existing.promoted:
                return []
            new_count = existing.evidence_count + evidence
            pattern = replace(
                existing,
                evidence_count=new_count,
                confidence=_confidence(new_count),
            )

        self.potential_rules[key] = pattern
        if pattern.promoted:
            return []
        if pattern.evidence_count >= self.MIN_EVIDENCE:
            self.potential_rules[key] = replace(pattern, promoted=True, confidence=1.0)
            return [self.induce_rule(pattern.antecedents, pattern.consequent)]
        return []

    def induce_rule(self, antecedents: Tuple[Node, ...], consequent: Node) -> Rule:
        return Rule(if_all=antecedents, then=consequent)


def _gather_relations(nodes: Iterable[Node]) -> List[Node]:
    relations: List[Node] = []
    stack = list(nodes)
    visited: set[str] = set()
    while stack:
        node = stack.pop()
        if node is None:
            continue
        fid = fingerprint(node)
        if fid in visited:
            continue
        visited.add(fid)
        if node.kind is NodeKind.REL:
            relations.append(node)
        stack.extend(node.args)
        if node.kind is NodeKind.STRUCT:
            stack.extend(node.fields.values())
    return relations


def _transitive_evidence(relations: List[Node]) -> Dict[str, int]:
    per_label = defaultdict(list)
    for rel in relations:
        if rel.label and len(rel.args) >= 2:
            head, tail = rel.args[0], rel.args[1]
            per_label[rel.label].append((fingerprint(head), fingerprint(tail)))
    evidence: Dict[str, int] = {}
    for label, edges in per_label.items():
        chains_found: set[Tuple[str, str, str]] = set()
        for start, mid in edges:
            for mid2, end in edges:
                if mid != mid2:
                    continue
                if start == end:
                    continue
                chain = (start, mid, end)
                chains_found.add(chain)
        if chains_found:
            evidence[label] = len(chains_found)
    return evidence


def _symmetric_evidence(relations: List[Node]) -> Dict[str, int]:
    per_label = defaultdict(list)
    for rel in relations:
        if rel.label and len(rel.args) >= 2:
            head, tail = rel.args[0], rel.args[1]
            per_label[rel.label].append((fingerprint(head), fingerprint(tail)))
    evidence: Dict[str, int] = {}
    for label, pairs in per_label.items():
        seen = set(pairs)
        symmetric_pairs = {
            tuple(sorted((a, b)))
            for (a, b) in pairs
            if (b, a) in seen and a != b
        }
        if symmetric_pairs:
            evidence[label] = len(symmetric_pairs)
    return evidence


def _confidence(evidence: int) -> float:
    return min(1.0, evidence / (evidence + 1.0))


def meta_learn(context: Tuple[Node, ...]) -> List[Rule]:
    engine = MetaLearningEngine()
    return engine.learn_from_trace(struct(), context)
