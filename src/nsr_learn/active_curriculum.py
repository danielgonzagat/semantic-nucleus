"""
Active Learning + Curriculum Learning: Aprendizado Inteligente.

ACTIVE LEARNING: O sistema DECIDE o que quer aprender.
- "Sobre o que devo perguntar para aprender mais rápido?"
- Maximiza informação por exemplo
- Reduz necessidade de dados rotulados

CURRICULUM LEARNING: O sistema ORGANIZA o que aprender.
- "Qual a melhor ordem para aprender?"
- Do simples ao complexo
- Constrói sobre conhecimento prévio

Juntos, permitem:
1. Aprendizado eficiente (poucos exemplos)
2. Aprendizado robusto (fundações sólidas)
3. Aprendizado autônomo (decide o que explorar)

Em redes neurais, isso é feito via uncertainty sampling + loss ordering.
Nós fazemos via CRITÉRIOS SIMBÓLICOS EXPLÍCITOS.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, Generic, Iterator, List, Mapping, Sequence, Set, Tuple, TypeVar
import math
import random


T = TypeVar("T")


# ==================== ACTIVE LEARNING ====================

class QueryStrategy(Enum):
    """Estratégias de seleção de queries."""
    
    UNCERTAINTY = auto()  # Maior incerteza
    DIVERSITY = auto()  # Maior diversidade
    EXPECTED_CHANGE = auto()  # Maior mudança esperada
    INFORMATION_GAIN = auto()  # Maior ganho de informação
    RANDOM = auto()  # Aleatório (baseline)


@dataclass
class Query:
    """Uma query para o oráculo."""
    
    instance: Any
    uncertainty_score: float = 0.0
    diversity_score: float = 0.0
    expected_value: float = 0.0
    
    @property
    def combined_score(self) -> float:
        """Score combinado (maior é mais informativo)."""
        return (
            0.4 * self.uncertainty_score +
            0.3 * self.diversity_score +
            0.3 * self.expected_value
        )


@dataclass
class LabeledExample:
    """Um exemplo com rótulo."""
    
    instance: Any
    label: Any
    confidence: float = 1.0
    source: str = "oracle"


class UncertaintyEstimator:
    """
    Estima incerteza do modelo sobre exemplos.
    
    Sem pesos neurais, usamos:
    - Distância de exemplos conhecidos
    - Consistência de regras
    - Cobertura de padrões
    """
    
    def __init__(self):
        self.known_examples: List[LabeledExample] = []
        self.predictions_cache: Dict[str, Dict[Any, int]] = defaultdict(lambda: defaultdict(int))
    
    def add_example(self, example: LabeledExample) -> None:
        self.known_examples.append(example)
    
    def estimate(self, instance: Any) -> float:
        """
        Estima incerteza sobre um instance (0 = certo, 1 = incerto).
        """
        if not self.known_examples:
            return 1.0  # Totalmente incerto sem exemplos
        
        # Fator 1: Distância dos exemplos conhecidos
        min_distance = self._min_distance(instance)
        distance_uncertainty = 1.0 - math.exp(-min_distance)
        
        # Fator 2: Consistência das previsões passadas
        key = str(instance)
        if key in self.predictions_cache:
            votes = self.predictions_cache[key]
            total = sum(votes.values())
            max_votes = max(votes.values())
            consistency = max_votes / total if total > 0 else 0.5
            consistency_uncertainty = 1.0 - consistency
        else:
            consistency_uncertainty = 0.5
        
        return 0.6 * distance_uncertainty + 0.4 * consistency_uncertainty
    
    def record_prediction(self, instance: Any, prediction: Any) -> None:
        """Registra uma previsão para análise de consistência."""
        key = str(instance)
        self.predictions_cache[key][prediction] += 1
    
    def _min_distance(self, instance: Any) -> float:
        """Calcula distância mínima para exemplos conhecidos."""
        if not self.known_examples:
            return float('inf')
        
        min_dist = float('inf')
        
        for example in self.known_examples:
            dist = self._distance(instance, example.instance)
            min_dist = min(min_dist, dist)
        
        return min_dist
    
    def _distance(self, a: Any, b: Any) -> float:
        """Calcula distância entre dois instances."""
        if isinstance(a, str) and isinstance(b, str):
            # Edit distance normalizada
            m, n = len(a), len(b)
            if m == 0:
                return float(n)
            if n == 0:
                return float(m)
            
            dp = [[0] * (n + 1) for _ in range(m + 1)]
            for i in range(m + 1):
                dp[i][0] = i
            for j in range(n + 1):
                dp[0][j] = j
            
            for i in range(1, m + 1):
                for j in range(1, n + 1):
                    if a[i-1] == b[j-1]:
                        dp[i][j] = dp[i-1][j-1]
                    else:
                        dp[i][j] = 1 + min(dp[i-1][j], dp[i][j-1], dp[i-1][j-1])
            
            return dp[m][n] / max(m, n)
        
        if isinstance(a, (int, float)) and isinstance(b, (int, float)):
            return abs(a - b)
        
        return 0.0 if a == b else 1.0


class DiversitySampler:
    """
    Amostra exemplos diversos para maximizar cobertura.
    """
    
    def __init__(self):
        self.sampled: List[Any] = []
    
    def add_sampled(self, instance: Any) -> None:
        self.sampled.append(instance)
    
    def score_diversity(self, candidate: Any) -> float:
        """
        Pontua diversidade de um candidato (maior = mais diverso).
        """
        if not self.sampled:
            return 1.0  # Primeiro é sempre diverso
        
        # Distância mínima para já amostrados
        min_dist = min(self._distance(candidate, s) for s in self.sampled)
        
        return min_dist
    
    def select_diverse(
        self,
        candidates: List[Any],
        n: int,
    ) -> List[Any]:
        """Seleciona N candidatos mais diversos."""
        selected = []
        remaining = list(candidates)
        
        for _ in range(min(n, len(remaining))):
            if not remaining:
                break
            
            # Seleciona o mais diverso do já selecionado
            scores = [
                (c, self._diversity_from_set(c, selected))
                for c in remaining
            ]
            
            best = max(scores, key=lambda x: x[1])[0]
            selected.append(best)
            remaining.remove(best)
        
        return selected
    
    def _distance(self, a: Any, b: Any) -> float:
        if isinstance(a, str) and isinstance(b, str):
            common = sum(1 for c1, c2 in zip(a, b) if c1 == c2)
            return 1.0 - common / max(len(a), len(b), 1)
        return 0.0 if a == b else 1.0
    
    def _diversity_from_set(self, candidate: Any, selected: List[Any]) -> float:
        if not selected:
            return 1.0
        return min(self._distance(candidate, s) for s in selected)


class ActiveLearner:
    """
    Sistema de active learning que decide o que perguntar.
    """
    
    def __init__(
        self,
        strategy: QueryStrategy = QueryStrategy.UNCERTAINTY,
        budget: int = 10,
    ):
        self.strategy = strategy
        self.budget = budget
        self.queries_made = 0
        
        self.uncertainty = UncertaintyEstimator()
        self.diversity = DiversitySampler()
        self.labeled_data: List[LabeledExample] = []
    
    def select_queries(
        self,
        pool: List[Any],
        n: int = 1,
    ) -> List[Query]:
        """
        Seleciona os melhores exemplos para consultar.
        """
        if self.queries_made >= self.budget:
            return []
        
        n = min(n, self.budget - self.queries_made)
        
        # Pontua cada candidato
        queries = []
        for instance in pool:
            q = Query(
                instance=instance,
                uncertainty_score=self.uncertainty.estimate(instance),
                diversity_score=self.diversity.score_diversity(instance),
                expected_value=self._expected_value(instance),
            )
            queries.append(q)
        
        # Ordena por estratégia
        if self.strategy == QueryStrategy.UNCERTAINTY:
            queries.sort(key=lambda q: q.uncertainty_score, reverse=True)
        elif self.strategy == QueryStrategy.DIVERSITY:
            queries.sort(key=lambda q: q.diversity_score, reverse=True)
        elif self.strategy == QueryStrategy.INFORMATION_GAIN:
            queries.sort(key=lambda q: q.combined_score, reverse=True)
        else:
            random.shuffle(queries)
        
        return queries[:n]
    
    def receive_label(
        self,
        instance: Any,
        label: Any,
        confidence: float = 1.0,
    ) -> None:
        """Recebe rótulo do oráculo."""
        example = LabeledExample(
            instance=instance,
            label=label,
            confidence=confidence,
        )
        
        self.labeled_data.append(example)
        self.uncertainty.add_example(example)
        self.diversity.add_sampled(instance)
        self.queries_made += 1
    
    def get_training_data(self) -> List[Tuple[Any, Any]]:
        """Retorna dados rotulados como pares (input, output)."""
        return [(ex.instance, ex.label) for ex in self.labeled_data]
    
    def _expected_value(self, instance: Any) -> float:
        """Estima valor esperado de conhecer o rótulo."""
        # Combinação de incerteza e diversidade
        unc = self.uncertainty.estimate(instance)
        div = self.diversity.score_diversity(instance)
        return 0.5 * unc + 0.5 * div


# ==================== CURRICULUM LEARNING ====================

class DifficultyMetric(Enum):
    """Métricas de dificuldade."""
    
    LENGTH = auto()  # Tamanho do input
    COMPLEXITY = auto()  # Complexidade estrutural
    SIMILARITY = auto()  # Similaridade com exemplos fáceis
    LOSS = auto()  # Erro do modelo atual


@dataclass
class CurriculumExample:
    """Um exemplo com metadados de currículo."""
    
    instance: Any
    label: Any
    difficulty: float = 0.0  # 0 = fácil, 1 = difícil
    stage: int = 0  # Estágio do currículo
    mastered: bool = False


@dataclass
class LearningStage:
    """Um estágio do currículo."""
    
    name: str
    examples: List[CurriculumExample] = field(default_factory=list)
    prerequisites: List[str] = field(default_factory=list)
    difficulty_range: Tuple[float, float] = (0.0, 1.0)
    mastery_threshold: float = 0.8
    
    @property
    def num_examples(self) -> int:
        return len(self.examples)
    
    @property
    def mastery_rate(self) -> float:
        if not self.examples:
            return 0.0
        return sum(1 for e in self.examples if e.mastered) / len(self.examples)
    
    @property
    def is_mastered(self) -> bool:
        return self.mastery_rate >= self.mastery_threshold


class DifficultyEstimator:
    """
    Estima dificuldade de exemplos.
    """
    
    def __init__(self, metric: DifficultyMetric = DifficultyMetric.LENGTH):
        self.metric = metric
        self.reference_examples: List[Tuple[Any, float]] = []  # (example, known_difficulty)
    
    def add_reference(self, example: Any, difficulty: float) -> None:
        """Adiciona exemplo de referência com dificuldade conhecida."""
        self.reference_examples.append((example, difficulty))
    
    def estimate(self, example: Any) -> float:
        """Estima dificuldade (0 = fácil, 1 = difícil)."""
        if self.metric == DifficultyMetric.LENGTH:
            return self._length_difficulty(example)
        elif self.metric == DifficultyMetric.COMPLEXITY:
            return self._complexity_difficulty(example)
        elif self.metric == DifficultyMetric.SIMILARITY:
            return self._similarity_difficulty(example)
        else:
            return 0.5
    
    def _length_difficulty(self, example: Any) -> float:
        """Dificuldade baseada em tamanho."""
        if isinstance(example, str):
            # Normaliza por tamanho máximo esperado
            return min(1.0, len(example) / 50)
        if isinstance(example, (list, tuple)):
            return min(1.0, len(example) / 20)
        return 0.5
    
    def _complexity_difficulty(self, example: Any) -> float:
        """Dificuldade baseada em complexidade estrutural."""
        if isinstance(example, str):
            # Conta caracteres únicos
            unique = len(set(example))
            total = len(example) or 1
            diversity = unique / total
            
            # Conta padrões (repetições)
            patterns = sum(1 for i in range(len(example)-1) if example[i] == example[i+1])
            pattern_ratio = patterns / total
            
            # Alta diversidade + poucos padrões = mais difícil
            return 0.5 * diversity + 0.5 * (1 - pattern_ratio)
        
        return 0.5
    
    def _similarity_difficulty(self, example: Any) -> float:
        """Dificuldade baseada em distância de exemplos fáceis."""
        if not self.reference_examples:
            return 0.5
        
        # Encontra referência mais similar
        min_dist = float('inf')
        ref_difficulty = 0.5
        
        for ref, diff in self.reference_examples:
            dist = self._distance(example, ref)
            if dist < min_dist:
                min_dist = dist
                ref_difficulty = diff
        
        # Se similar a um fácil, é fácil
        if min_dist < 0.3:
            return ref_difficulty
        
        # Se distante de tudo, é mais difícil
        return min(1.0, ref_difficulty + 0.3)
    
    def _distance(self, a: Any, b: Any) -> float:
        if isinstance(a, str) and isinstance(b, str):
            # Jaccard de caracteres
            set_a = set(a)
            set_b = set(b)
            inter = len(set_a & set_b)
            union = len(set_a | set_b)
            return 1.0 - inter / union if union > 0 else 1.0
        return 0.0 if a == b else 1.0


class CurriculumLearner:
    """
    Sistema de curriculum learning que organiza o aprendizado.
    """
    
    def __init__(
        self,
        num_stages: int = 3,
        examples_per_stage: int | None = None,
    ):
        self.num_stages = num_stages
        self.examples_per_stage = examples_per_stage
        
        self.difficulty_estimator = DifficultyEstimator()
        self.stages: List[LearningStage] = []
        self.current_stage_idx: int = 0
        
        # Histórico de aprendizado
        self.learning_curve: List[Tuple[int, float]] = []  # (num_examples, accuracy)
    
    def create_curriculum(
        self,
        examples: List[Tuple[Any, Any]],
    ) -> List[LearningStage]:
        """
        Cria currículo a partir de exemplos.
        
        Ordena por dificuldade e divide em estágios.
        """
        # Estima dificuldade de cada exemplo
        curriculum_examples = []
        for inp, out in examples:
            difficulty = self.difficulty_estimator.estimate(inp)
            curriculum_examples.append(CurriculumExample(
                instance=inp,
                label=out,
                difficulty=difficulty,
            ))
        
        # Ordena por dificuldade
        curriculum_examples.sort(key=lambda e: e.difficulty)
        
        # Divide em estágios
        self.stages = []
        stage_size = len(curriculum_examples) // self.num_stages or 1
        
        for i in range(self.num_stages):
            start = i * stage_size
            end = start + stage_size if i < self.num_stages - 1 else len(curriculum_examples)
            
            stage_examples = curriculum_examples[start:end]
            
            # Atribui estágio aos exemplos
            for ex in stage_examples:
                ex.stage = i
            
            min_diff = stage_examples[0].difficulty if stage_examples else 0.0
            max_diff = stage_examples[-1].difficulty if stage_examples else 1.0
            
            stage = LearningStage(
                name=f"Stage_{i+1}",
                examples=stage_examples,
                prerequisites=[f"Stage_{i}"] if i > 0 else [],
                difficulty_range=(min_diff, max_diff),
            )
            
            self.stages.append(stage)
        
        return self.stages
    
    def get_next_batch(self, batch_size: int = 10) -> List[CurriculumExample]:
        """
        Retorna próximo batch de exemplos para treinar.
        
        Respeita o currículo: só avança quando estágio atual é dominado.
        """
        if not self.stages:
            return []
        
        # Verifica se pode avançar
        while (self.current_stage_idx < len(self.stages) - 1 and
               self.stages[self.current_stage_idx].is_mastered):
            self.current_stage_idx += 1
        
        current = self.stages[self.current_stage_idx]
        
        # Retorna exemplos não dominados do estágio atual
        not_mastered = [e for e in current.examples if not e.mastered]
        
        if not_mastered:
            return not_mastered[:batch_size]
        
        # Se todos dominados, inclui do próximo estágio
        if self.current_stage_idx < len(self.stages) - 1:
            next_stage = self.stages[self.current_stage_idx + 1]
            return next_stage.examples[:batch_size]
        
        return current.examples[:batch_size]
    
    def mark_mastered(self, instance: Any, success: bool) -> None:
        """Marca um exemplo como dominado ou não."""
        for stage in self.stages:
            for example in stage.examples:
                if example.instance == instance:
                    example.mastered = success
                    return
    
    def update_learning_curve(self, num_examples: int, accuracy: float) -> None:
        """Atualiza curva de aprendizado."""
        self.learning_curve.append((num_examples, accuracy))
    
    def get_progress(self) -> Dict[str, Any]:
        """Retorna progresso no currículo."""
        return {
            "current_stage": self.current_stage_idx,
            "total_stages": len(self.stages),
            "stage_name": self.stages[self.current_stage_idx].name if self.stages else None,
            "stage_mastery": self.stages[self.current_stage_idx].mastery_rate if self.stages else 0,
            "total_mastered": sum(
                1 for s in self.stages for e in s.examples if e.mastered
            ),
            "total_examples": sum(len(s.examples) for s in self.stages),
        }
    
    def should_advance(self) -> bool:
        """Verifica se deve avançar para próximo estágio."""
        if not self.stages or self.current_stage_idx >= len(self.stages) - 1:
            return False
        
        return self.stages[self.current_stage_idx].is_mastered


class AdaptiveLearner:
    """
    Combina active learning + curriculum learning.
    
    Decide:
    1. O QUE perguntar (active)
    2. QUANDO perguntar (curriculum)
    """
    
    def __init__(
        self,
        query_budget: int = 50,
        num_stages: int = 3,
    ):
        self.active = ActiveLearner(
            strategy=QueryStrategy.INFORMATION_GAIN,
            budget=query_budget,
        )
        self.curriculum = CurriculumLearner(num_stages=num_stages)
        
        self.learned_examples: List[Tuple[Any, Any]] = []
    
    def initialize(
        self,
        unlabeled_pool: List[Any],
        initial_labels: List[Tuple[Any, Any]] | None = None,
    ) -> None:
        """
        Inicializa o learner.
        
        Args:
            unlabeled_pool: Pool de exemplos não rotulados
            initial_labels: Exemplos iniciais já rotulados
        """
        # Processa exemplos iniciais
        if initial_labels:
            for instance, label in initial_labels:
                self.active.receive_label(instance, label)
                self.learned_examples.append((instance, label))
            
            # Cria currículo inicial
            self.curriculum.create_curriculum(initial_labels)
    
    def get_next_query(
        self,
        pool: List[Any],
    ) -> Query | None:
        """
        Decide o próximo exemplo para consultar.
        
        Combina incerteza do active learning com estágio do curriculum.
        """
        # Filtra pool pelo estágio atual do currículo
        if self.curriculum.stages:
            current_stage = self.curriculum.stages[self.curriculum.current_stage_idx]
            min_diff, max_diff = current_stage.difficulty_range
            
            # Prefere exemplos na faixa de dificuldade do estágio
            filtered = []
            for item in pool:
                diff = self.curriculum.difficulty_estimator.estimate(item)
                if min_diff <= diff <= max_diff:
                    filtered.append(item)
            
            if filtered:
                pool = filtered
        
        queries = self.active.select_queries(pool, n=1)
        return queries[0] if queries else None
    
    def receive_answer(
        self,
        instance: Any,
        label: Any,
    ) -> None:
        """Recebe resposta do oráculo."""
        self.active.receive_label(instance, label)
        self.learned_examples.append((instance, label))
        
        # Atualiza currículo
        self.curriculum.mark_mastered(instance, True)
        
        # Recria currículo se necessário
        if len(self.learned_examples) % 10 == 0:
            self.curriculum.create_curriculum(self.learned_examples)
    
    def get_training_data(self) -> List[Tuple[Any, Any]]:
        """Retorna dados de treino ordenados pelo currículo."""
        if not self.curriculum.stages:
            return self.learned_examples
        
        # Ordena por estágio
        ordered = []
        for stage in self.curriculum.stages:
            for ex in stage.examples:
                ordered.append((ex.instance, ex.label))
        
        return ordered
    
    def get_status(self) -> Dict[str, Any]:
        """Retorna status do aprendizado."""
        return {
            "queries_made": self.active.queries_made,
            "budget_remaining": self.active.budget - self.active.queries_made,
            "examples_learned": len(self.learned_examples),
            "curriculum_progress": self.curriculum.get_progress(),
        }


__all__ = [
    # Active Learning
    "QueryStrategy",
    "Query",
    "LabeledExample",
    "UncertaintyEstimator",
    "DiversitySampler",
    "ActiveLearner",
    # Curriculum Learning
    "DifficultyMetric",
    "CurriculumExample",
    "LearningStage",
    "DifficultyEstimator",
    "CurriculumLearner",
    # Combined
    "AdaptiveLearner",
]
