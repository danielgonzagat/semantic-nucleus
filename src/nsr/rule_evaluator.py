"""
Sistema de Avaliação e Evolução de Regras.

Avalia regras aprendidas e evolui as melhores, removendo as piores.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, TYPE_CHECKING

from .state import Rule
from .weightless_types import Episode

if TYPE_CHECKING:
    from .weightless_learning import WeightlessLearner


@dataclass()
class RuleEvaluation:
    """Avaliação de uma regra."""
    
    rule: Rule
    fingerprint: str
    # Métricas
    times_applied: int = 0
    times_successful: int = 0
    times_failed: int = 0
    avg_quality_improvement: float = 0.0
    # Score final
    fitness_score: float = 0.0


class RuleEvaluator:
    """
    Avalia e evolui regras aprendidas.
    
    Remove regras ruins, mantém regras boas, evolui regras promissoras.
    """
    
    def __init__(self, min_fitness: float = 0.3, min_applications: int = 5):
        self.min_fitness = min_fitness
        self.min_applications = min_applications
        self.evaluations: Dict[str, RuleEvaluation] = {}
    
    def evaluate_rule(
        self,
        rule: Rule,
        episodes: List[Episode],
        learner: WeightlessLearner,
    ) -> RuleEvaluation:
        """Avalia uma regra contra episódios."""
        
        rule_fp = self._rule_fingerprint(rule)
        
        if rule_fp in self.evaluations:
            eval_obj = self.evaluations[rule_fp]
        else:
            eval_obj = RuleEvaluation(rule=rule, fingerprint=rule_fp)
            self.evaluations[rule_fp] = eval_obj
        
        # Testa regra em episódios
        successful = 0
        failed = 0
        quality_improvements = []
        
        for episode in episodes:
            # Verifica se regra se aplica
            if self._rule_applies(rule, episode):
                eval_obj.times_applied += 1
                
                # Verifica se resultado é bom
                if episode.quality >= 0.6:
                    successful += 1
                    quality_improvements.append(episode.quality)
                else:
                    failed += 1
        
        eval_obj.times_successful = successful
        eval_obj.times_failed = failed
        
        if quality_improvements:
            eval_obj.avg_quality_improvement = sum(quality_improvements) / len(
                quality_improvements
            )
        
        # Calcula fitness
        eval_obj.fitness_score = self._calculate_fitness(eval_obj)
        
        return eval_obj
    
    def _rule_applies(self, rule: Rule, episode: Episode) -> bool:
        """Verifica se regra se aplica a um episódio."""
        from .rules import unify
        
        # Verifica se antecedentes da regra unificam com relações do episódio
        for antecedent in rule.if_all:
            for rel in episode.relations:
                bindings = {}
                if unify(antecedent, rel, bindings) is not None:
                    return True
        return False
    
    def _calculate_fitness(self, evaluation: RuleEvaluation) -> float:
        """Calcula fitness de uma regra."""
        if evaluation.times_applied == 0:
            return 0.0
        
        # Taxa de sucesso
        success_rate = evaluation.times_successful / max(1, evaluation.times_applied)
        
        # Melhoria de qualidade média
        quality_bonus = min(1.0, evaluation.avg_quality_improvement)
        
        # Penaliza se não foi aplicada o suficiente
        application_penalty = min(
            1.0, evaluation.times_applied / max(1, self.min_applications)
        )
        
        # Fitness = combinação ponderada
        fitness = (success_rate * 0.5) + (quality_bonus * 0.3) + (
            application_penalty * 0.2
        )
        
        return fitness
    
    def filter_good_rules(self, evaluations: List[RuleEvaluation]) -> List[Rule]:
        """Filtra apenas regras boas (fitness acima do threshold)."""
        good = [
            eval_obj.rule
            for eval_obj in evaluations
            if eval_obj.fitness_score >= self.min_fitness
            and eval_obj.times_applied >= self.min_applications
        ]
        return good
    
    def evolve_rules(
        self, rules: List[Rule], episodes: List[Episode], learner: WeightlessLearner
    ) -> Tuple[List[Rule], List[Rule]]:
        """
        Evolui regras: avalia, mantém boas, remove ruins.
        
        Retorna: (regras_mantidas, regras_removidas)
        """
        # Avalia todas as regras
        evaluations = [
            self.evaluate_rule(rule, episodes, learner) for rule in rules
        ]
        
        # Filtra boas
        good_rules = self.filter_good_rules(evaluations)
        
        # Regras removidas
        good_fps = {self._rule_fingerprint(rule) for rule in good_rules}
        removed_rules = [
            rule
            for rule in rules
            if self._rule_fingerprint(rule) not in good_fps
        ]
        
        return good_rules, removed_rules
    
    def _rule_fingerprint(self, rule: Rule) -> str:
        """Cria fingerprint de uma regra."""
        from hashlib import blake2b
        from liu import fingerprint
        
        hasher = blake2b(digest_size=16)
        for antecedent in rule.if_all:
            hasher.update(fingerprint(antecedent).encode("utf-8"))
        hasher.update(fingerprint(rule.then).encode("utf-8"))
        return hasher.hexdigest()


__all__ = ["RuleEvaluator", "RuleEvaluation"]
