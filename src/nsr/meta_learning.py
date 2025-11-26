"""
Meta-Learning: Indução de regras determinísticas a partir de padrões de execução bem-sucedidos.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple, Optional

from liu import Node, NodeKind, struct, text, list_node, entity, fingerprint, relation, var
from nsr.state import Rule

@dataclass(frozen=True)
class LearnedPattern:
    antecedents: Tuple[Node, ...]
    consequent: Node
    confidence: float
    evidence_count: int

class MetaLearningEngine:
    """
    Motor de aprendizado que observa resoluções de problemas e tenta generalizar regras.
    """
    
    def __init__(self):
        self.potential_rules: List[LearnedPattern] = []

    def learn_from_trace(self, trace_summary: Node, context: Tuple[Node, ...]) -> List[Rule]:
        """
        Analisa um trace de execução bem sucedida e induz regras determinísticas simples.
        Atualmente suportamos duas heurísticas:
        - Transitividade: R(a,b) + R(b,c) => R(a,c)
        - Simetria: R(a,b) => R(b,a)
        """
        relations = [
            node
            for node in context
            if node.kind is NodeKind.REL and len(node.args) >= 2
        ]
        if not relations:
            return []
        candidates: List[Rule] = []
        candidates.extend(self._derive_transitive_rules(relations))
        candidates.extend(self._derive_symmetric_rules(relations))
        return self._dedup_rules(candidates)

    def _derive_transitive_rules(self, relations: List[Node]) -> List[Rule]:
        labels: set[str] = set()
        for rel1 in relations:
            for rel2 in relations:
                if rel1 is rel2:
                    continue
                if rel1.label != rel2.label:
                    continue
                if rel1.args[1] != rel2.args[0]:
                    continue
                if not rel1.label:
                    continue
                labels.add(rel1.label)
        rules: List[Rule] = []
        for label in sorted(labels):
            x, y, z = var("?X"), var("?Y"), var("?Z")
            rule = Rule(
                if_all=(relation(label, x, y), relation(label, y, z)),
                then=relation(label, x, z),
            )
            rules.append(rule)
        return rules

    def _derive_symmetric_rules(self, relations: List[Node]) -> List[Rule]:
        labels: set[str] = set()
        for rel in relations:
            for counterpart in relations:
                if rel is counterpart:
                    continue
                if rel.label != counterpart.label:
                    continue
                if rel.args[0] == counterpart.args[1] and rel.args[1] == counterpart.args[0]:
                    if rel.label:
                        labels.add(rel.label)
        rules: List[Rule] = []
        for label in sorted(labels):
            x, y = var("?X"), var("?Y")
            rule = Rule(
                if_all=(relation(label, x, y),),
                then=relation(label, y, x),
            )
            rules.append(rule)
        return rules

    def _dedup_rules(self, candidates: List[Rule]) -> List[Rule]:
        seen: set[Tuple[str, ...]] = set()
        unique: List[Rule] = []
        for rule in candidates:
            signature = tuple(fingerprint(node) for node in (*rule.if_all, rule.then))
            if signature in seen:
                continue
            seen.add(signature)
            unique.append(rule)
        return unique

    def induce_rule(self, antecedent: Node, consequent: Node) -> Rule:
        # Cria uma regra formal
        return Rule(if_all=(antecedent,), then=consequent)

# Placeholder para integração futura
def meta_learn(context: Tuple[Node, ...]) -> List[Rule]:
    engine = MetaLearningEngine()
    return engine.learn_from_trace(struct(), context)
