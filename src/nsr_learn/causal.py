"""
Raciocínio Causal: Entender Causa e Efeito Sem Pesos Neurais.

Correlação ≠ Causalidade

LLMs aprendem correlações estatísticas nos dados.
Nós aprendemos ESTRUTURAS CAUSAIS explícitas.

Teoria Base: Causal Inference (Pearl, 2000)
- Grafos causais direcionados acíclicos (DAGs)
- Intervenções: do(X=x) vs observar X=x
- Contrafactuais: "O que teria acontecido se...?"

Níveis de raciocínio causal (Ladder of Causation):
1. Associação: P(Y|X) - "O que observo?"
2. Intervenção: P(Y|do(X)) - "O que acontece se eu fizer X?"
3. Contrafactual: P(Y_x|X=x', Y=y') - "E se X tivesse sido diferente?"

Isso permite:
- Distinguir causa de correlação
- Prever efeitos de intervenções
- Responder "por quê?"
- Raciocinar sobre cenários hipotéticos
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, FrozenSet, Iterator, List, Mapping, Sequence, Set, Tuple
import math


@dataclass(frozen=True)
class CausalVariable:
    """Uma variável no grafo causal."""
    
    name: str
    domain: Tuple[Any, ...]  # Valores possíveis
    
    def __str__(self) -> str:
        return self.name


@dataclass(frozen=True)
class CausalLink:
    """Uma aresta causal: X → Y."""
    
    cause: str  # Nome da variável causa
    effect: str  # Nome da variável efeito
    strength: float = 1.0  # Força da relação causal
    
    def __str__(self) -> str:
        return f"{self.cause} → {self.effect}"


@dataclass
class ConditionalProbability:
    """
    Tabela de probabilidade condicional P(Y|Parents(Y)).
    
    Representação discreta de como os pais afetam a variável.
    """
    
    variable: str
    parents: Tuple[str, ...]
    table: Dict[Tuple[Any, ...], Dict[Any, float]] = field(default_factory=dict)
    
    def set_probability(
        self,
        parent_values: Tuple[Any, ...],
        value: Any,
        prob: float,
    ) -> None:
        """Define P(variable=value | parents=parent_values)."""
        if parent_values not in self.table:
            self.table[parent_values] = {}
        self.table[parent_values][value] = prob
    
    def get_probability(
        self,
        parent_values: Tuple[Any, ...],
        value: Any,
    ) -> float:
        """Retorna P(variable=value | parents=parent_values)."""
        if parent_values not in self.table:
            return 0.0
        return self.table[parent_values].get(value, 0.0)
    
    def sample(
        self,
        parent_values: Tuple[Any, ...],
    ) -> Any:
        """Amostra um valor dado os valores dos pais."""
        if parent_values not in self.table:
            return None
        
        dist = self.table[parent_values]
        total = sum(dist.values())
        
        if total == 0:
            return None
        
        # Retorna valor mais provável (determinístico)
        return max(dist.items(), key=lambda x: x[1])[0]


@dataclass
class CausalGraph:
    """
    Grafo Causal Direcionado Acíclico (DAG).
    
    Representa a estrutura causal entre variáveis.
    """
    
    variables: Dict[str, CausalVariable] = field(default_factory=dict)
    links: List[CausalLink] = field(default_factory=list)
    cpts: Dict[str, ConditionalProbability] = field(default_factory=dict)
    
    # Índices
    _parents: Dict[str, Set[str]] = field(default_factory=lambda: defaultdict(set))
    _children: Dict[str, Set[str]] = field(default_factory=lambda: defaultdict(set))
    
    def add_variable(self, var: CausalVariable) -> None:
        """Adiciona uma variável ao grafo."""
        self.variables[var.name] = var
    
    def add_link(self, cause: str, effect: str, strength: float = 1.0) -> None:
        """Adiciona uma aresta causal."""
        link = CausalLink(cause, effect, strength)
        self.links.append(link)
        self._parents[effect].add(cause)
        self._children[cause].add(effect)
    
    def set_cpt(self, cpt: ConditionalProbability) -> None:
        """Define a CPT de uma variável."""
        self.cpts[cpt.variable] = cpt
    
    def get_parents(self, var: str) -> Set[str]:
        """Retorna os pais de uma variável."""
        return self._parents.get(var, set())
    
    def get_children(self, var: str) -> Set[str]:
        """Retorna os filhos de uma variável."""
        return self._children.get(var, set())
    
    def get_ancestors(self, var: str) -> Set[str]:
        """Retorna todos os ancestrais."""
        ancestors = set()
        to_visit = list(self.get_parents(var))
        
        while to_visit:
            current = to_visit.pop()
            if current in ancestors:
                continue
            ancestors.add(current)
            to_visit.extend(self.get_parents(current))
        
        return ancestors
    
    def get_descendants(self, var: str) -> Set[str]:
        """Retorna todos os descendentes."""
        descendants = set()
        to_visit = list(self.get_children(var))
        
        while to_visit:
            current = to_visit.pop()
            if current in descendants:
                continue
            descendants.add(current)
            to_visit.extend(self.get_children(current))
        
        return descendants
    
    def is_ancestor(self, var1: str, var2: str) -> bool:
        """Verifica se var1 é ancestral de var2."""
        return var1 in self.get_ancestors(var2)
    
    def topological_order(self) -> List[str]:
        """Retorna variáveis em ordem topológica."""
        in_degree = {v: len(self.get_parents(v)) for v in self.variables}
        queue = [v for v, d in in_degree.items() if d == 0]
        order = []
        
        while queue:
            var = queue.pop(0)
            order.append(var)
            
            for child in self.get_children(var):
                in_degree[child] -= 1
                if in_degree[child] == 0:
                    queue.append(child)
        
        return order
    
    def is_d_separated(
        self,
        x: str,
        y: str,
        z: Set[str],
    ) -> bool:
        """
        Verifica se X e Y são d-separados dado Z.
        
        D-separação implica independência condicional.
        """
        # Implementação simplificada
        # Verifica se há caminho ativo entre X e Y dado Z
        
        # Se Z bloqueia todos os caminhos, são d-separados
        visited = set()
        queue = [(x, "up")]  # (nó, direção)
        
        while queue:
            node, direction = queue.pop(0)
            
            if (node, direction) in visited:
                continue
            visited.add((node, direction))
            
            if node == y:
                return False  # Encontrou caminho ativo
            
            # Regras de d-separação
            if direction == "up":
                # Vindo de um filho
                if node not in z:
                    # Não está em Z, continua para pais
                    for parent in self.get_parents(node):
                        queue.append((parent, "up"))
                    # E para outros filhos
                    for child in self.get_children(node):
                        if child != x:
                            queue.append((child, "down"))
                # Collider: só ativa se está em Z ou tem descendente em Z
                if node in z or z & self.get_descendants(node):
                    for parent in self.get_parents(node):
                        queue.append((parent, "up"))
            
            else:  # direction == "down"
                # Vindo de um pai
                if node not in z:
                    # Não bloqueado, continua
                    for child in self.get_children(node):
                        queue.append((child, "down"))
                    for parent in self.get_parents(node):
                        queue.append((parent, "up"))
        
        return True


@dataclass
class Intervention:
    """
    Uma intervenção do(X=x).
    
    Diferente de observar X=x, intervir remove as causas de X.
    """
    
    variable: str
    value: Any
    
    def __str__(self) -> str:
        return f"do({self.variable}={self.value})"


@dataclass
class CausalQuery:
    """Uma query causal."""
    
    target: str  # Variável alvo
    target_value: Any | None = None  # Valor específico (opcional)
    given: Dict[str, Any] = field(default_factory=dict)  # Condições observadas
    interventions: List[Intervention] = field(default_factory=list)  # Intervenções
    
    @property
    def is_observational(self) -> bool:
        return len(self.interventions) == 0
    
    @property
    def is_interventional(self) -> bool:
        return len(self.interventions) > 0
    
    def __str__(self) -> str:
        parts = [f"P({self.target}"]
        
        if self.target_value is not None:
            parts[0] = f"P({self.target}={self.target_value}"
        
        conditions = []
        
        for var, val in self.given.items():
            conditions.append(f"{var}={val}")
        
        for intervention in self.interventions:
            conditions.append(str(intervention))
        
        if conditions:
            parts.append(" | ")
            parts.append(", ".join(conditions))
        
        parts.append(")")
        return "".join(parts)


class CausalReasoner:
    """
    Motor de raciocínio causal.
    
    Suporta:
    1. Queries observacionais P(Y|X)
    2. Queries interventionais P(Y|do(X))
    3. Identificação de efeitos causais
    4. Contrafactuais
    """
    
    def __init__(self, graph: CausalGraph):
        self.graph = graph
    
    def query(self, q: CausalQuery) -> Dict[Any, float]:
        """
        Responde uma query causal.
        
        Retorna distribuição de probabilidade sobre valores do target.
        """
        if q.is_observational:
            return self._observational_query(q)
        else:
            return self._interventional_query(q)
    
    def identify_effect(
        self,
        cause: str,
        effect: str,
    ) -> Dict[str, Any]:
        """
        Identifica se o efeito causal é identificável.
        
        Usa critérios como:
        - Back-door criterion
        - Front-door criterion
        """
        result = {
            "identifiable": False,
            "adjustment_set": None,
            "method": None,
        }
        
        # Tenta back-door criterion
        backdoor_set = self._find_backdoor_set(cause, effect)
        if backdoor_set is not None:
            result["identifiable"] = True
            result["adjustment_set"] = backdoor_set
            result["method"] = "back-door"
            return result
        
        # Tenta front-door criterion
        frontdoor_set = self._find_frontdoor_set(cause, effect)
        if frontdoor_set is not None:
            result["identifiable"] = True
            result["adjustment_set"] = frontdoor_set
            result["method"] = "front-door"
            return result
        
        return result
    
    def estimate_causal_effect(
        self,
        cause: str,
        effect: str,
        data: List[Dict[str, Any]],
    ) -> float:
        """
        Estima o efeito causal de cause sobre effect.
        
        Usa ajuste por backdoor se possível.
        """
        identification = self.identify_effect(cause, effect)
        
        if not identification["identifiable"]:
            return 0.0
        
        adjustment_set = identification["adjustment_set"]
        
        # Estima E[effect | do(cause=1)] - E[effect | do(cause=0)]
        # Usando ajuste por backdoor
        
        if not adjustment_set:
            # Efeito direto
            effect_given_cause = self._conditional_mean(data, effect, {cause: True})
            effect_given_no_cause = self._conditional_mean(data, effect, {cause: False})
            return effect_given_cause - effect_given_no_cause
        
        # Com ajuste
        total_effect = 0.0
        
        for stratum in self._get_strata(data, adjustment_set):
            weight = len(stratum) / len(data)
            effect_1 = self._conditional_mean(stratum, effect, {cause: True})
            effect_0 = self._conditional_mean(stratum, effect, {cause: False})
            total_effect += weight * (effect_1 - effect_0)
        
        return total_effect
    
    def counterfactual(
        self,
        factual: Dict[str, Any],
        intervention: Intervention,
        target: str,
    ) -> Any:
        """
        Responde query contrafactual.
        
        "Dado que observamos factual, o que teria acontecido
        se tivéssemos intervido?"
        """
        # 1. Abdução: infere valores das variáveis exógenas
        exogenous = self._abduction(factual)
        
        # 2. Intervenção: modifica o grafo
        modified_graph = self._intervene_graph(intervention)
        
        # 3. Predição: propaga para encontrar o target
        result = self._predict_with_exogenous(modified_graph, exogenous, target)
        
        return result
    
    def explain_why(
        self,
        observation: Dict[str, Any],
        target: str,
    ) -> List[str]:
        """
        Explica por que target tem certo valor.
        
        Identifica causas que contribuíram.
        """
        target_value = observation.get(target)
        
        if target_value is None:
            return ["Valor do target não observado"]
        
        explanations = []
        
        # Identifica causas diretas
        parents = self.graph.get_parents(target)
        
        for parent in parents:
            parent_value = observation.get(parent)
            if parent_value is not None:
                # Verifica se o pai contribuiu
                link = next(
                    (l for l in self.graph.links if l.cause == parent and l.effect == target),
                    None
                )
                if link:
                    explanations.append(
                        f"{parent}={parent_value} causou {target}={target_value} "
                        f"(força: {link.strength:.2f})"
                    )
        
        if not explanations:
            explanations.append(f"{target}={target_value} não tem causas conhecidas")
        
        return explanations
    
    def _observational_query(self, q: CausalQuery) -> Dict[Any, float]:
        """Responde query observacional P(Y|X)."""
        target_var = self.graph.variables.get(q.target)
        
        if target_var is None:
            return {}
        
        result = {}
        
        for value in target_var.domain:
            prob = self._compute_conditional_prob(q.target, value, q.given)
            result[value] = prob
        
        return result
    
    def _interventional_query(self, q: CausalQuery) -> Dict[Any, float]:
        """Responde query interventional P(Y|do(X))."""
        # Modifica o grafo removendo arestas para variáveis intervindas
        for intervention in q.interventions:
            # Remove os pais da variável intervinda
            self.graph._parents[intervention.variable] = set()
        
        # Agora é uma query observacional no grafo modificado
        obs_query = CausalQuery(
            target=q.target,
            target_value=q.target_value,
            given={
                **q.given,
                **{i.variable: i.value for i in q.interventions}
            },
        )
        
        return self._observational_query(obs_query)
    
    def _find_backdoor_set(
        self,
        cause: str,
        effect: str,
    ) -> Set[str] | None:
        """Encontra conjunto de ajuste backdoor."""
        # Candidatos: não-descendentes do cause
        descendants = self.graph.get_descendants(cause)
        candidates = set(self.graph.variables.keys()) - descendants - {cause, effect}
        
        # Verifica se algum subconjunto satisfaz backdoor
        # Simplificação: usa todos os não-descendentes que são pais do cause
        parents_of_cause = self.graph.get_parents(cause)
        
        if parents_of_cause:
            # Verifica se bloqueia todos os caminhos backdoor
            if self.graph.is_d_separated(cause, effect, parents_of_cause):
                return parents_of_cause
        
        return set() if not parents_of_cause else None
    
    def _find_frontdoor_set(
        self,
        cause: str,
        effect: str,
    ) -> Set[str] | None:
        """Encontra conjunto de ajuste frontdoor."""
        # Mediadores: filhos do cause que são ancestrais do effect
        children = self.graph.get_children(cause)
        ancestors_of_effect = self.graph.get_ancestors(effect)
        
        mediators = children & ancestors_of_effect
        
        if mediators:
            return mediators
        
        return None
    
    def _compute_conditional_prob(
        self,
        target: str,
        value: Any,
        given: Dict[str, Any],
    ) -> float:
        """Computa P(target=value | given)."""
        cpt = self.graph.cpts.get(target)
        
        if cpt is None:
            return 1.0 / len(self.graph.variables.get(target, CausalVariable("", ())).domain)
        
        # Coleta valores dos pais
        parent_values = tuple(given.get(p, None) for p in cpt.parents)
        
        if None in parent_values:
            # Marginaliza sobre pais não conhecidos
            return 0.5  # Simplificação
        
        return cpt.get_probability(parent_values, value)
    
    def _conditional_mean(
        self,
        data: List[Dict[str, Any]],
        target: str,
        conditions: Dict[str, Any],
    ) -> float:
        """Calcula média condicional."""
        matching = [
            d for d in data
            if all(d.get(k) == v for k, v in conditions.items())
        ]
        
        if not matching:
            return 0.0
        
        values = [d.get(target, 0) for d in matching]
        
        if all(isinstance(v, bool) for v in values):
            return sum(1 for v in values if v) / len(values)
        
        return sum(values) / len(values)
    
    def _get_strata(
        self,
        data: List[Dict[str, Any]],
        variables: Set[str],
    ) -> List[List[Dict[str, Any]]]:
        """Divide dados em estratos."""
        strata = defaultdict(list)
        
        for d in data:
            key = tuple(d.get(v) for v in sorted(variables))
            strata[key].append(d)
        
        return list(strata.values())
    
    def _abduction(self, observation: Dict[str, Any]) -> Dict[str, Any]:
        """Infere variáveis exógenas das observações."""
        # Simplificação: retorna as observações como proxy
        return dict(observation)
    
    def _intervene_graph(self, intervention: Intervention) -> CausalGraph:
        """Cria grafo modificado pela intervenção."""
        # Copia o grafo
        new_graph = CausalGraph()
        new_graph.variables = dict(self.graph.variables)
        
        for link in self.graph.links:
            if link.effect != intervention.variable:
                new_graph.add_link(link.cause, link.effect, link.strength)
        
        return new_graph
    
    def _predict_with_exogenous(
        self,
        graph: CausalGraph,
        exogenous: Dict[str, Any],
        target: str,
    ) -> Any:
        """Prediz target dado exógenas e grafo modificado."""
        return exogenous.get(target)


def learn_causal_structure(
    data: List[Dict[str, Any]],
    variables: List[str],
) -> CausalGraph:
    """
    Aprende estrutura causal de dados observacionais.
    
    Usa testes de independência condicional (PC algorithm simplificado).
    """
    graph = CausalGraph()
    
    # Adiciona variáveis
    for var in variables:
        values = tuple(set(d.get(var) for d in data if d.get(var) is not None))
        graph.add_variable(CausalVariable(var, values))
    
    # Inicialmente, assume grafo completo
    edges = set()
    for v1 in variables:
        for v2 in variables:
            if v1 != v2:
                edges.add((v1, v2))
    
    # Remove arestas por independência
    for v1, v2 in list(edges):
        # Testa se v1 ⊥ v2
        if _are_independent(data, v1, v2):
            edges.discard((v1, v2))
            edges.discard((v2, v1))
    
    # Orienta arestas (simplificado: ordem temporal se disponível)
    for v1, v2 in edges:
        if (v2, v1) in edges:
            # Escolhe orientação baseada em ordem lexicográfica
            if v1 < v2:
                edges.discard((v2, v1))
            else:
                edges.discard((v1, v2))
    
    # Adiciona ao grafo
    for v1, v2 in edges:
        graph.add_link(v1, v2)
    
    return graph


def _are_independent(
    data: List[Dict[str, Any]],
    var1: str,
    var2: str,
    threshold: float = 0.1,
) -> bool:
    """Testa independência entre duas variáveis."""
    # Usa correlação como proxy
    values1 = [d.get(var1, 0) for d in data]
    values2 = [d.get(var2, 0) for d in data]
    
    # Converte booleanos para int
    values1 = [int(v) if isinstance(v, bool) else v for v in values1]
    values2 = [int(v) if isinstance(v, bool) else v for v in values2]
    
    if not values1 or not values2:
        return True
    
    # Correlação simples
    n = len(values1)
    mean1 = sum(values1) / n
    mean2 = sum(values2) / n
    
    cov = sum((v1 - mean1) * (v2 - mean2) for v1, v2 in zip(values1, values2)) / n
    
    std1 = math.sqrt(sum((v - mean1) ** 2 for v in values1) / n)
    std2 = math.sqrt(sum((v - mean2) ** 2 for v in values2) / n)
    
    if std1 == 0 or std2 == 0:
        return True
    
    correlation = abs(cov / (std1 * std2))
    
    return correlation < threshold


__all__ = [
    "CausalVariable",
    "CausalLink",
    "ConditionalProbability",
    "CausalGraph",
    "Intervention",
    "CausalQuery",
    "CausalReasoner",
    "learn_causal_structure",
]
