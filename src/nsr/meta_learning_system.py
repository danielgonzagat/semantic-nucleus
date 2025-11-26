"""
Meta-Aprendizado: Aprende a aprender melhor.

Sistema que aprende quais estratégias de aprendizado funcionam melhor.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

from .weightless_learning import Episode, WeightlessLearner
from .rule_evaluator import RuleEvaluation


@dataclass(slots=True)
class LearningStrategy:
    """Estratégia de aprendizado."""
    
    name: str
    # Parâmetros da estratégia
    min_pattern_support: int
    min_confidence: float
    auto_learn_interval: int
    # Performance
    rules_learned: int = 0
    rules_accepted: int = 0
    avg_rule_quality: float = 0.0
    success_rate: float = 0.0


class MetaLearningSystem:
    """
    Sistema que aprende qual estratégia de aprendizado funciona melhor.
    
    Testa diferentes estratégias e adapta parâmetros baseado em performance.
    """
    
    def __init__(self):
        self.strategies: Dict[str, LearningStrategy] = {}
        self.strategy_performance: Dict[str, List[float]] = {}
        self.best_strategy: str | None = None
    
    def create_strategy(
        self,
        name: str,
        min_pattern_support: int = 3,
        min_confidence: float = 0.6,
        auto_learn_interval: int = 50,
    ) -> LearningStrategy:
        """Cria nova estratégia de aprendizado."""
        
        strategy = LearningStrategy(
            name=name,
            min_pattern_support=min_pattern_support,
            min_confidence=min_confidence,
            auto_learn_interval=auto_learn_interval,
        )
        
        self.strategies[name] = strategy
        self.strategy_performance[name] = []
        
        return strategy
    
    def evaluate_strategy(
        self, strategy_name: str, learner: WeightlessLearner
    ) -> float:
        """Avalia performance de uma estratégia."""
        
        if strategy_name not in self.strategies:
            return 0.0
        
        strategy = self.strategies[strategy_name]
        
        # Métricas de performance
        total_rules = len(learner.learned_rules)
        if total_rules == 0:
            return 0.0
        
        # Avalia qualidade das regras
        if learner.rule_evaluator:
            evaluations = []
            for rule in learner.learned_rules:
                # Simplificação: assume avaliação básica
                evaluations.append(0.7)  # Placeholder
            
            avg_quality = sum(evaluations) / len(evaluations) if evaluations else 0.0
        else:
            avg_quality = 0.5
        
        # Score = combinação de métricas
        score = (total_rules * 0.3) + (avg_quality * 0.7)
        
        # Atualiza estratégia
        strategy.rules_learned = total_rules
        strategy.avg_rule_quality = avg_quality
        strategy.success_rate = avg_quality
        
        # Registra performance
        self.strategy_performance[strategy_name].append(score)
        
        # Mantém apenas últimas 100 avaliações
        if len(self.strategy_performance[strategy_name]) > 100:
            self.strategy_performance[strategy_name] = self.strategy_performance[
                strategy_name
            ][-100:]
        
        return score
    
    def select_best_strategy(self) -> str | None:
        """Seleciona melhor estratégia baseado em performance."""
        
        if not self.strategies:
            return None
        
        best_name = None
        best_avg_score = 0.0
        
        for name, scores in self.strategy_performance.items():
            if not scores:
                continue
            
            avg_score = sum(scores) / len(scores)
            if avg_score > best_avg_score:
                best_avg_score = avg_score
                best_name = name
        
        self.best_strategy = best_name
        return best_name
    
    def adapt_parameters(
        self, learner: WeightlessLearner, episodes: List[Episode]
    ) -> WeightlessLearner:
        """
        Adapta parâmetros do learner baseado em performance.
        
        Ajusta min_pattern_support, min_confidence, etc.
        """
        
        # Se temos poucos episódios, reduz threshold
        if len(episodes) < 20:
            learner.min_pattern_support = 2
            learner.min_confidence = 0.5
        elif len(episodes) < 100:
            learner.min_pattern_support = 3
            learner.min_confidence = 0.6
        else:
            # Com muitos episódios, pode ser mais seletivo
            learner.min_pattern_support = 5
            learner.min_confidence = 0.7
        
        # Ajusta intervalo de aprendizado baseado em quantidade de episódios
        if len(episodes) > 1000:
            learner.auto_learn_interval = 100
        elif len(episodes) > 500:
            learner.auto_learn_interval = 75
        else:
            learner.auto_learn_interval = 50
        
        return learner


__all__ = ["LearningStrategy", "MetaLearningSystem"]
