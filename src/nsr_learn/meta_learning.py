"""
Meta-Learning Simbólico: Aprender a Aprender Sem Pesos Neurais.

Meta-learning permite adaptação rápida a novas tarefas.
Em redes neurais, isso é feito via MAML, Reptile, etc.

Nossa abordagem SIMBÓLICA:

1. BIBLIOTECA DE ESTRATÉGIAS: Estratégias de aprendizado reutilizáveis
2. SELEÇÃO DE ESTRATÉGIA: Escolher a melhor para cada tarefa
3. TRANSFERÊNCIA ESTRUTURAL: Reusar estruturas entre tarefas
4. ABSTRAÇÃO DE TAREFAS: Identificar padrões entre tarefas

Níveis de meta-learning:
- Nível 0: Aprender uma tarefa específica
- Nível 1: Aprender COMO aprender tarefas similares
- Nível 2: Aprender QUANDO usar qual estratégia

Isso permite:
- Few-shot learning (aprender de poucos exemplos)
- Transfer learning (transferir conhecimento)
- Adaptação rápida (sem retreinamento massivo)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, Generic, Iterator, List, Mapping, Sequence, Set, Tuple, TypeVar
import time


T = TypeVar("T")


class TaskType(Enum):
    """Tipos de tarefas reconhecidos."""
    
    CLASSIFICATION = auto()  # Classificar exemplos
    SEQUENCE = auto()  # Prever sequências
    TRANSFORMATION = auto()  # Transformar inputs
    ANALOGY = auto()  # Completar analogias
    REASONING = auto()  # Raciocínio lógico
    UNKNOWN = auto()


@dataclass
class Task:
    """Uma tarefa de aprendizado."""
    
    name: str
    task_type: TaskType
    examples: List[Tuple[Any, Any]]  # (input, output)
    test_cases: List[Tuple[Any, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def num_examples(self) -> int:
        return len(self.examples)
    
    @property
    def is_few_shot(self) -> bool:
        return self.num_examples <= 5
    
    def get_training_data(self) -> Tuple[List[Any], List[Any]]:
        """Retorna inputs e outputs separados."""
        inputs = [x for x, _ in self.examples]
        outputs = [y for _, y in self.examples]
        return inputs, outputs


@dataclass
class LearningStrategy(ABC):
    """Estratégia abstrata de aprendizado."""
    
    name: str
    applicable_types: Set[TaskType]
    complexity: int  # Menor = mais simples/rápido
    
    @abstractmethod
    def learn(self, task: Task) -> "LearnedModel":
        """Aprende de uma tarefa."""
        pass
    
    @abstractmethod
    def can_handle(self, task: Task) -> bool:
        """Verifica se pode lidar com a tarefa."""
        pass


@dataclass
class LearnedModel:
    """Modelo aprendido por uma estratégia."""
    
    strategy_name: str
    predict: Callable[[Any], Any]
    confidence: float = 1.0
    training_time: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __call__(self, x: Any) -> Any:
        return self.predict(x)


class MemoizationStrategy(LearningStrategy):
    """
    Estratégia de memorização: guarda exemplos e busca similar.
    
    Funciona bem para: tarefas com poucos exemplos distintos.
    """
    
    def __init__(self):
        super().__init__(
            name="memoization",
            applicable_types={TaskType.CLASSIFICATION, TaskType.TRANSFORMATION},
            complexity=1,
        )
    
    def learn(self, task: Task) -> LearnedModel:
        start = time.time()
        
        # Memoriza exemplos
        memory = {str(x): y for x, y in task.examples}
        
        def predict(x: Any) -> Any:
            key = str(x)
            if key in memory:
                return memory[key]
            
            # Busca similar (por prefixo)
            for mem_key, mem_val in memory.items():
                if mem_key.startswith(key[:3]) or key.startswith(mem_key[:3]):
                    return mem_val
            
            return None
        
        return LearnedModel(
            strategy_name=self.name,
            predict=predict,
            confidence=1.0 if task.examples else 0.0,
            training_time=time.time() - start,
            metadata={"memory_size": len(memory)},
        )
    
    def can_handle(self, task: Task) -> bool:
        return task.task_type in self.applicable_types


class PatternMatchingStrategy(LearningStrategy):
    """
    Estratégia de pattern matching: encontra padrões nos dados.
    
    Funciona bem para: transformações com padrões regulares.
    """
    
    def __init__(self):
        super().__init__(
            name="pattern_matching",
            applicable_types={TaskType.TRANSFORMATION, TaskType.SEQUENCE},
            complexity=3,
        )
    
    def learn(self, task: Task) -> LearnedModel:
        start = time.time()
        
        patterns = []
        
        for inp, out in task.examples:
            if isinstance(inp, str) and isinstance(out, str):
                pattern = self._extract_pattern(inp, out)
                if pattern:
                    patterns.append(pattern)
        
        def predict(x: Any) -> Any:
            if not isinstance(x, str):
                return None
            
            for pattern_type, pattern_data in patterns:
                result = self._apply_pattern(x, pattern_type, pattern_data)
                if result is not None:
                    return result
            
            return None
        
        return LearnedModel(
            strategy_name=self.name,
            predict=predict,
            confidence=len(patterns) / max(1, len(task.examples)),
            training_time=time.time() - start,
            metadata={"patterns_found": len(patterns)},
        )
    
    def can_handle(self, task: Task) -> bool:
        if task.task_type not in self.applicable_types:
            return False
        
        # Verifica se exemplos são strings
        return all(
            isinstance(x, str) and isinstance(y, str)
            for x, y in task.examples
        )
    
    def _extract_pattern(
        self,
        inp: str,
        out: str,
    ) -> Tuple[str, Any] | None:
        """Extrai padrão de um par input-output."""
        # Padrão: uppercase
        if out == inp.upper():
            return ("upper", None)
        
        # Padrão: lowercase
        if out == inp.lower():
            return ("lower", None)
        
        # Padrão: reverse
        if out == inp[::-1]:
            return ("reverse", None)
        
        # Padrão: prefix
        if out.endswith(inp):
            return ("prefix", out[:-len(inp)])
        
        # Padrão: suffix
        if out.startswith(inp):
            return ("suffix", out[len(inp):])
        
        # Padrão: replace
        for i, (c1, c2) in enumerate(zip(inp, out)):
            if c1 != c2:
                if inp.replace(c1, c2) == out:
                    return ("replace", (c1, c2))
        
        return None
    
    def _apply_pattern(
        self,
        x: str,
        pattern_type: str,
        pattern_data: Any,
    ) -> str | None:
        """Aplica padrão a um input."""
        if pattern_type == "upper":
            return x.upper()
        elif pattern_type == "lower":
            return x.lower()
        elif pattern_type == "reverse":
            return x[::-1]
        elif pattern_type == "prefix":
            return pattern_data + x
        elif pattern_type == "suffix":
            return x + pattern_data
        elif pattern_type == "replace":
            old, new = pattern_data
            return x.replace(old, new)
        
        return None


class RuleInductionStrategy(LearningStrategy):
    """
    Estratégia de indução de regras: extrai regras if-then.
    
    Funciona bem para: classificação com features discretas.
    """
    
    def __init__(self):
        super().__init__(
            name="rule_induction",
            applicable_types={TaskType.CLASSIFICATION, TaskType.REASONING},
            complexity=5,
        )
    
    def learn(self, task: Task) -> LearnedModel:
        start = time.time()
        
        rules = self._induce_rules(task.examples)
        
        def predict(x: Any) -> Any:
            for condition, result in rules:
                if self._matches_condition(x, condition):
                    return result
            
            # Default: classe mais comum
            if task.examples:
                outputs = [y for _, y in task.examples]
                return max(set(outputs), key=outputs.count)
            
            return None
        
        return LearnedModel(
            strategy_name=self.name,
            predict=predict,
            confidence=self._evaluate_rules(rules, task.examples),
            training_time=time.time() - start,
            metadata={"num_rules": len(rules)},
        )
    
    def can_handle(self, task: Task) -> bool:
        return task.task_type in self.applicable_types
    
    def _induce_rules(
        self,
        examples: List[Tuple[Any, Any]],
    ) -> List[Tuple[Any, Any]]:
        """Induz regras dos exemplos."""
        rules = []
        
        # Agrupa por output
        by_output: Dict[Any, List[Any]] = defaultdict(list)
        for inp, out in examples:
            by_output[out].append(inp)
        
        # Para cada classe, encontra condições que a distinguem
        for output, inputs in by_output.items():
            # Condição simples: features comuns
            if inputs:
                common = self._find_common_features(inputs)
                if common:
                    rules.append((common, output))
        
        return rules
    
    def _find_common_features(self, inputs: List[Any]) -> Any:
        """Encontra features comuns nos inputs."""
        if not inputs:
            return None
        
        if all(isinstance(x, str) for x in inputs):
            # Para strings, encontra prefixo/sufixo comum
            common_prefix = inputs[0]
            for inp in inputs[1:]:
                while not inp.startswith(common_prefix):
                    common_prefix = common_prefix[:-1]
                    if not common_prefix:
                        break
            
            if common_prefix:
                return ("prefix", common_prefix)
        
        if all(isinstance(x, (int, float)) for x in inputs):
            # Para números, encontra range
            min_val = min(inputs)
            max_val = max(inputs)
            return ("range", (min_val, max_val))
        
        return None
    
    def _matches_condition(self, x: Any, condition: Any) -> bool:
        """Verifica se x satisfaz a condição."""
        if condition is None:
            return True
        
        cond_type, cond_data = condition
        
        if cond_type == "prefix" and isinstance(x, str):
            return x.startswith(cond_data)
        
        if cond_type == "range" and isinstance(x, (int, float)):
            min_val, max_val = cond_data
            return min_val <= x <= max_val
        
        return False
    
    def _evaluate_rules(
        self,
        rules: List[Tuple[Any, Any]],
        examples: List[Tuple[Any, Any]],
    ) -> float:
        """Avalia acurácia das regras."""
        if not examples:
            return 0.0
        
        correct = 0
        for inp, expected in examples:
            for condition, result in rules:
                if self._matches_condition(inp, condition):
                    if result == expected:
                        correct += 1
                    break
        
        return correct / len(examples)


class AnalogyStrategy(LearningStrategy):
    """
    Estratégia de analogia: resolve por mapeamento estrutural.
    
    Funciona bem para: tarefas de analogia e transferência.
    """
    
    def __init__(self):
        super().__init__(
            name="analogy",
            applicable_types={TaskType.ANALOGY, TaskType.TRANSFORMATION},
            complexity=4,
        )
    
    def learn(self, task: Task) -> LearnedModel:
        start = time.time()
        
        # Extrai mapeamentos dos exemplos
        mappings = []
        
        for inp, out in task.examples:
            mapping = self._extract_mapping(inp, out)
            if mapping:
                mappings.append(mapping)
        
        def predict(x: Any) -> Any:
            for mapping in mappings:
                result = self._apply_mapping(x, mapping)
                if result is not None:
                    return result
            return None
        
        return LearnedModel(
            strategy_name=self.name,
            predict=predict,
            confidence=len(mappings) / max(1, len(task.examples)),
            training_time=time.time() - start,
            metadata={"mappings": len(mappings)},
        )
    
    def can_handle(self, task: Task) -> bool:
        return task.task_type in self.applicable_types
    
    def _extract_mapping(self, inp: Any, out: Any) -> Dict[str, str] | None:
        """Extrai mapeamento elemento por elemento."""
        if isinstance(inp, str) and isinstance(out, str):
            if len(inp) == len(out):
                mapping = {}
                for c1, c2 in zip(inp, out):
                    if c1 in mapping and mapping[c1] != c2:
                        return None
                    mapping[c1] = c2
                return mapping
        
        return None
    
    def _apply_mapping(
        self,
        x: Any,
        mapping: Dict[str, str],
    ) -> Any | None:
        """Aplica mapeamento a um input."""
        if isinstance(x, str):
            result = ""
            for c in x:
                if c in mapping:
                    result += mapping[c]
                else:
                    result += c
            return result
        
        return None


@dataclass
class StrategyPerformance:
    """Performance de uma estratégia em uma tarefa."""
    
    strategy_name: str
    accuracy: float
    training_time: float
    prediction_time: float
    
    @property
    def score(self) -> float:
        """Score combinado (maior é melhor)."""
        return self.accuracy - 0.01 * self.training_time


class MetaLearner:
    """
    Meta-learner que escolhe e combina estratégias.
    
    Aprende quais estratégias funcionam para quais tipos de tarefas.
    """
    
    def __init__(self):
        self.strategies: List[LearningStrategy] = [
            MemoizationStrategy(),
            PatternMatchingStrategy(),
            RuleInductionStrategy(),
            AnalogyStrategy(),
        ]
        
        # Histórico de performance por tipo de tarefa
        self.performance_history: Dict[TaskType, List[StrategyPerformance]] = defaultdict(list)
        
        # Cache de modelos por tarefa
        self.model_cache: Dict[str, LearnedModel] = {}
    
    def learn(self, task: Task) -> LearnedModel:
        """
        Aprende uma tarefa usando a melhor estratégia.
        """
        # Verifica cache
        if task.name in self.model_cache:
            return self.model_cache[task.name]
        
        # Identifica tipo de tarefa se necessário
        if task.task_type == TaskType.UNKNOWN:
            task.task_type = self._infer_task_type(task)
        
        # Seleciona estratégia
        strategy = self._select_strategy(task)
        
        # Aprende
        model = strategy.learn(task)
        
        # Avalia
        if task.test_cases:
            performance = self._evaluate_model(model, task)
            self.performance_history[task.task_type].append(performance)
        
        # Cacheia
        self.model_cache[task.name] = model
        
        return model
    
    def few_shot_learn(
        self,
        examples: List[Tuple[Any, Any]],
        task_name: str = "unnamed",
    ) -> LearnedModel:
        """
        Aprende de poucos exemplos.
        
        Usa meta-conhecimento para compensar poucos dados.
        """
        task = Task(
            name=task_name,
            task_type=TaskType.UNKNOWN,
            examples=examples,
        )
        
        return self.learn(task)
    
    def transfer_learn(
        self,
        source_task: Task,
        target_examples: List[Tuple[Any, Any]],
    ) -> LearnedModel:
        """
        Transfere aprendizado de uma tarefa fonte.
        """
        # Aprende tarefa fonte
        source_model = self.learn(source_task)
        
        # Cria tarefa alvo com exemplos
        target_task = Task(
            name=f"{source_task.name}_transfer",
            task_type=source_task.task_type,
            examples=target_examples,
        )
        
        # Combina modelos
        target_model = self.learn(target_task)
        
        # Modelo combinado: tenta target primeiro, depois source
        def combined_predict(x: Any) -> Any:
            result = target_model(x)
            if result is not None:
                return result
            return source_model(x)
        
        return LearnedModel(
            strategy_name="transfer_combined",
            predict=combined_predict,
            confidence=(source_model.confidence + target_model.confidence) / 2,
        )
    
    def recommend_strategy(
        self,
        task_type: TaskType,
    ) -> LearningStrategy:
        """
        Recomenda a melhor estratégia para um tipo de tarefa.
        
        Usa histórico de performance.
        """
        history = self.performance_history.get(task_type, [])
        
        if not history:
            # Sem histórico, usa heurística de complexidade
            applicable = [s for s in self.strategies if task_type in s.applicable_types]
            return min(applicable, key=lambda s: s.complexity) if applicable else self.strategies[0]
        
        # Agrupa por estratégia
        by_strategy: Dict[str, List[float]] = defaultdict(list)
        for perf in history:
            by_strategy[perf.strategy_name].append(perf.score)
        
        # Escolhe com melhor score médio
        best_name = max(by_strategy.keys(), key=lambda n: sum(by_strategy[n]) / len(by_strategy[n]))
        
        return next(s for s in self.strategies if s.name == best_name)
    
    def _select_strategy(self, task: Task) -> LearningStrategy:
        """Seleciona a melhor estratégia para uma tarefa."""
        # Filtra estratégias aplicáveis
        applicable = [
            s for s in self.strategies
            if s.can_handle(task)
        ]
        
        if not applicable:
            return self.strategies[0]  # Default
        
        # Usa histórico se disponível
        if self.performance_history.get(task.task_type):
            return self.recommend_strategy(task.task_type)
        
        # Heurística: usa a mais simples primeiro
        return min(applicable, key=lambda s: s.complexity)
    
    def _infer_task_type(self, task: Task) -> TaskType:
        """Infere o tipo de tarefa dos exemplos."""
        if not task.examples:
            return TaskType.UNKNOWN
        
        inputs = [x for x, _ in task.examples]
        outputs = [y for _, y in task.examples]
        
        # Classificação: outputs são classes discretas (poucos valores únicos)
        unique_outputs = set(str(y) for y in outputs)
        if len(unique_outputs) <= min(5, len(outputs) / 2):
            return TaskType.CLASSIFICATION
        
        # Sequência: inputs são índices numéricos
        if all(isinstance(x, int) for x in inputs):
            return TaskType.SEQUENCE
        
        # Transformação: strings para strings
        if all(isinstance(x, str) and isinstance(y, str) for x, y in task.examples):
            return TaskType.TRANSFORMATION
        
        return TaskType.UNKNOWN
    
    def _evaluate_model(
        self,
        model: LearnedModel,
        task: Task,
    ) -> StrategyPerformance:
        """Avalia modelo nos casos de teste."""
        if not task.test_cases:
            return StrategyPerformance(
                strategy_name=model.strategy_name,
                accuracy=model.confidence,
                training_time=model.training_time,
                prediction_time=0.0,
            )
        
        correct = 0
        start = time.time()
        
        for inp, expected in task.test_cases:
            result = model(inp)
            if result == expected:
                correct += 1
        
        prediction_time = time.time() - start
        accuracy = correct / len(task.test_cases)
        
        return StrategyPerformance(
            strategy_name=model.strategy_name,
            accuracy=accuracy,
            training_time=model.training_time,
            prediction_time=prediction_time,
        )


__all__ = [
    "TaskType",
    "Task",
    "LearningStrategy",
    "LearnedModel",
    "MemoizationStrategy",
    "PatternMatchingStrategy",
    "RuleInductionStrategy",
    "AnalogyStrategy",
    "StrategyPerformance",
    "MetaLearner",
]
