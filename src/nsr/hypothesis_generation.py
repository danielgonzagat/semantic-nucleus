"""
Geração de Hipóteses: Gera e testa hipóteses sobre padrões.

Sistema que formula hipóteses sobre relações e as testa contra dados.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Set, Tuple

from liu import Node, NodeKind, relation, var

from .weightless_types import Episode
from .state import Rule


@dataclass(frozen=True, slots=True)
class Hypothesis:
    """Hipótese sobre uma relação."""
    
    rule: Rule
    confidence: float  # Confiança inicial
    support: int  # Quantos episódios suportam
    counterexamples: int  # Quantos episódios contradizem
    tested: bool = False


class HypothesisGenerator:
    """
    Gera hipóteses sobre padrões e as testa.
    
    Processo:
    1. Observa padrões frequentes
    2. Gera hipóteses (regras candidatas)
    3. Testa hipóteses contra episódios
    4. Aceita/rejeita baseado em evidência
    """
    
    def __init__(self, min_support: int = 3, min_confidence: float = 0.6):
        self.min_support = min_support
        self.min_confidence = min_confidence
        self.hypotheses: List[Hypothesis] = []
        self.accepted_rules: List[Rule] = []
    
    def generate_from_episodes(self, episodes: List[Episode]) -> List[Hypothesis]:
        """Gera hipóteses a partir de episódios."""
        
        # Extrai padrões de relações
        relation_patterns = self._extract_relation_patterns(episodes)
        
        # Gera hipóteses
        hypotheses = []
        for pattern in relation_patterns:
            if pattern["count"] < self.min_support:
                continue
            
            # Cria regra candidata
            rule = self._pattern_to_rule(pattern)
            
            # Calcula confiança inicial
            confidence = pattern["count"] / len(episodes)
            
            hypothesis = Hypothesis(
                rule=rule,
                confidence=confidence,
                support=pattern["count"],
                counterexamples=0,
                tested=False,
            )
            
            hypotheses.append(hypothesis)
        
        self.hypotheses.extend(hypotheses)
        return hypotheses
    
    def test_hypothesis(
        self, hypothesis: Hypothesis, episodes: List[Episode]
    ) -> Hypothesis:
        """Testa hipótese contra episódios."""
        
        support = 0
        counterexamples = 0
        
        for episode in episodes:
            # Verifica se regra se aplica
            if self._rule_applies(hypothesis.rule, episode):
                # Verifica se consequência é verdadeira
                if self._consequence_true(hypothesis.rule, episode):
                    support += 1
                else:
                    counterexamples += 1
        
        # Atualiza confiança
        total = support + counterexamples
        confidence = support / max(1, total)
        
        # Cria hipótese atualizada
        updated = Hypothesis(
            rule=hypothesis.rule,
            confidence=confidence,
            support=support,
            counterexamples=counterexamples,
            tested=True,
        )
        
        return updated
    
    def accept_or_reject(self, hypothesis: Hypothesis) -> bool:
        """Aceita ou rejeita hipótese baseado em evidência."""
        
        if not hypothesis.tested:
            return False
        
        if hypothesis.support < self.min_support:
            return False
        
        if hypothesis.confidence < self.min_confidence:
            return False
        
        # Aceita se confiança alta e poucos contra-exemplos
        if hypothesis.confidence >= self.min_confidence and hypothesis.counterexamples < hypothesis.support:
            self.accepted_rules.append(hypothesis.rule)
            return True
        
        return False
    
    def _extract_relation_patterns(
        self, episodes: List[Episode]
    ) -> List[Dict]:
        """Extrai padrões de relações dos episódios."""
        from collections import Counter
        
        patterns: Counter[Tuple[str, str, str]] = Counter()
        
        for episode in episodes:
            for rel in episode.relations:
                if rel.kind is NodeKind.REL and len(rel.args) >= 2:
                    label = rel.label or ""
                    arg1 = rel.args[0].label if rel.args[0].kind is NodeKind.ENTITY else "?"
                    arg2 = rel.args[1].label if rel.args[1].kind is NodeKind.ENTITY else "?"
                    patterns[(label, arg1, arg2)] += 1
        
        # Converte para lista de dicionários
        result = []
        for (label, arg1, arg2), count in patterns.items():
            result.append({
                "label": label,
                "arg1": arg1,
                "arg2": arg2,
                "count": count,
            })
        
        return result
    
    def _pattern_to_rule(self, pattern: Dict) -> Rule:
        """Converte padrão em regra."""
        # Simplificação: cria regra genérica
        # Em produção, analisaria padrões mais complexos
        from liu import entity
        
        if pattern["arg1"] == "?" or pattern["arg2"] == "?":
            # Usa variáveis
            antecedent = relation(pattern["label"], var("?X"), var("?Y"))
            consequent = relation(pattern["label"], var("?X"), var("?Y"))
        else:
            # Usa entidades específicas
            antecedent = relation(pattern["label"], entity(pattern["arg1"]), entity(pattern["arg2"]))
            consequent = relation(pattern["label"], entity(pattern["arg1"]), entity(pattern["arg2"]))
        
        return Rule(if_all=(antecedent,), then=consequent)
    
    def _rule_applies(self, rule: Rule, episode: Episode) -> bool:
        """Verifica se regra se aplica a um episódio."""
        from .rules import unify
        
        for antecedent in rule.if_all:
            for rel in episode.relations:
                bindings = {}
                if unify(antecedent, rel, bindings) is not None:
                    return True
        return False
    
    def _consequence_true(self, rule: Rule, episode: Episode) -> bool:
        """Verifica se consequência da regra é verdadeira no episódio."""
        from .rules import unify, substitute
        
        # Aplica regra para obter consequência
        for antecedent in rule.if_all:
            for rel in episode.relations:
                bindings = {}
                if unify(antecedent, rel, bindings) is not None:
                    # Substitui na consequência
                    consequence = substitute(rule.then, bindings)
                    # Verifica se consequência está nas relações
                    for ep_rel in episode.relations:
                        if ep_rel == consequence:
                            return True
        return False


__all__ = ["Hypothesis", "HypothesisGenerator"]
