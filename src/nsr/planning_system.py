"""
Sistema de Planejamento: Raciocina sobre ações para alcançar objetivos.

Aprende quais ações são boas para alcançar quais objetivos.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Set, Tuple

from liu import Node, NodeKind, fingerprint


@dataclass(frozen=True, slots=True)
class Action:
    """Ação que pode ser executada."""
    
    name: str
    preconditions: Tuple[Node, ...]  # Condições necessárias
    effects: Tuple[Node, ...]  # Efeitos da ação
    cost: float = 1.0  # Custo da ação


@dataclass(frozen=True, slots=True)
class Plan:
    """Plano: sequência de ações para alcançar objetivo."""
    
    actions: Tuple[Action, ...]
    goal: Node
    cost: float  # Custo total
    success_probability: float  # Probabilidade de sucesso


@dataclass(slots=True)
class PlanningSystem:
    """
    Sistema de planejamento que aprende quais ações funcionam.
    
    Aprende:
    - Quais ações levam a quais estados
    - Quais sequências de ações alcançam objetivos
    - Heurísticas para busca eficiente
    """
    
    # Ações conhecidas
    actions: Dict[str, Action] = field(default_factory=dict)
    
    # Experiências: (estado_inicial, ação, estado_final, sucesso)
    experiences: List[Tuple[Node, Action, Node, bool]] = field(default_factory=list)
    
    # Heurísticas aprendidas: estado -> estimativa de custo para objetivo
    heuristics: Dict[str, float] = field(default_factory=dict)
    
    # Planos bem-sucedidos
    successful_plans: List[Plan] = field(default_factory=list)
    
    def add_action(self, action: Action) -> None:
        """Adiciona ação ao sistema."""
        self.actions[action.name] = action
    
    def observe_execution(
        self, initial_state: Node, action: Action, final_state: Node, success: bool
    ) -> None:
        """Observa execução de uma ação."""
        self.experiences.append((initial_state, action, final_state, success))
        
        # Atualiza heurística se ação foi bem-sucedida
        if success:
            self._update_heuristic(initial_state, final_state, action.cost)
    
    def plan(self, initial_state: Node, goal: Node, max_depth: int = 10) -> Plan | None:
        """
        Planeja sequência de ações para alcançar objetivo.
        
        Usa busca com heurísticas aprendidas.
        """
        # Busca em largura com heurística
        from collections import deque
        
        queue = deque([(initial_state, [], 0.0)])  # (estado, ações, custo)
        visited: Set[str] = set()
        
        while queue:
            current_state, actions_so_far, cost_so_far = queue.popleft()
            
            state_key = fingerprint(current_state)
            if state_key in visited:
                continue
            visited.add(state_key)
            
            # Verifica se alcançou objetivo
            if self._goal_achieved(current_state, goal):
                plan_actions = [self.actions[name] for name in actions_so_far if name in self.actions]
                return Plan(
                    actions=tuple(plan_actions),
                    goal=goal,
                    cost=cost_so_far,
                    success_probability=self._estimate_success_probability(plan_actions),
                )
            
            # Limite de profundidade
            if len(actions_so_far) >= max_depth:
                continue
            
            # Gera ações possíveis
            possible_actions = self._get_possible_actions(current_state)
            
            for action in possible_actions:
                # Estima estado resultante
                estimated_state = self._estimate_result(current_state, action)
                
                # Calcula custo estimado
                estimated_cost = cost_so_far + action.cost
                heuristic_cost = self._get_heuristic(estimated_state, goal)
                total_cost = estimated_cost + heuristic_cost
                
                # Adiciona à fila (ordenada por custo total)
                new_actions = actions_so_far + [action.name]
                queue.append((estimated_state, new_actions, estimated_cost))
            
            # Ordena fila por custo total
            queue = deque(sorted(queue, key=lambda x: x[2] + self._get_heuristic(x[0], goal)))
        
        return None
    
    def learn_from_experience(self) -> None:
        """Aprende heurísticas e ações a partir de experiências."""
        
        # Agrupa experiências por ação
        action_experiences: Dict[str, List[Tuple[Node, Node, bool]]] = defaultdict(list)
        
        for initial, action, final, success in self.experiences:
            action_experiences[action.name].append((initial, final, success))
        
        # Aprende padrões de cada ação
        for action_name, experiences in action_experiences.items():
            if len(experiences) < 3:
                continue
            
            # Calcula taxa de sucesso
            success_count = sum(1 for _, _, s in experiences if s)
            success_rate = success_count / len(experiences)
            
            # Atualiza custo da ação baseado em sucesso
            if action_name in self.actions:
                # Ações com baixa taxa de sucesso têm custo maior
                action = self.actions[action_name]
                adjusted_cost = action.cost / max(0.1, success_rate)
                # Em produção, atualizaria ação
                # Por enquanto, apenas registra
    
    def _get_possible_actions(self, state: Node) -> List[Action]:
        """Retorna ações possíveis no estado atual."""
        possible = []
        
        for action in self.actions.values():
            if self._preconditions_met(state, action):
                possible.append(action)
        
        return possible
    
    def _preconditions_met(self, state: Node, action: Action) -> bool:
        """Verifica se precondições da ação são satisfeitas."""
        # Simplificação: verifica se precondições estão no estado
        # Em produção, faria matching mais sofisticado
        state_relations = self._extract_relations(state)
        precondition_relations = self._extract_relations_from_list(action.preconditions)
        
        # Verifica se todas as precondições estão no estado
        for prec in precondition_relations:
            if prec not in state_relations:
                return False
        
        return True
    
    def _estimate_result(self, state: Node, action: Action) -> Node:
        """Estima estado resultante de executar ação."""
        # Simplificação: adiciona efeitos ao estado
        # Em produção, faria transformação mais sofisticada
        from liu import struct
        
        state_relations = list(self._extract_relations(state))
        effect_relations = list(self._extract_relations_from_list(action.effects))
        
        # Combina estado com efeitos
        new_relations = state_relations + effect_relations
        
        # Cria novo estado (simplificado)
        return struct(relations=tuple(new_relations))
    
    def _goal_achieved(self, state: Node, goal: Node) -> bool:
        """Verifica se objetivo foi alcançado."""
        state_relations = self._extract_relations(state)
        goal_relations = self._extract_relations(goal)
        
        # Verifica se todas as relações do objetivo estão no estado
        for goal_rel in goal_relations:
            if goal_rel not in state_relations:
                return False
        
        return True
    
    def _get_heuristic(self, state: Node, goal: Node) -> float:
        """Retorna heurística (estimativa de custo) para alcançar objetivo."""
        state_key = fingerprint(state)
        goal_key = fingerprint(goal)
        heuristic_key = f"{state_key}:{goal_key}"
        
        if heuristic_key in self.heuristics:
            return self.heuristics[heuristic_key]
        
        # Heurística padrão: número de relações faltando
        state_relations = set(self._extract_relations(state))
        goal_relations = set(self._extract_relations(goal))
        missing = len(goal_relations - state_relations)
        
        return float(missing)
    
    def _update_heuristic(self, initial: Node, final: Node, cost: float) -> None:
        """Atualiza heurística baseado em experiência."""
        initial_key = fingerprint(initial)
        final_key = fingerprint(final)
        heuristic_key = f"{initial_key}:{final_key}"
        
        # Atualiza com média móvel
        if heuristic_key in self.heuristics:
            self.heuristics[heuristic_key] = (self.heuristics[heuristic_key] + cost) / 2.0
        else:
            self.heuristics[heuristic_key] = cost
    
    def _estimate_success_probability(self, actions: List[Action]) -> float:
        """Estima probabilidade de sucesso de um plano."""
        if not actions:
            return 0.0
        
        # Baseado em experiências anteriores
        success_rates = []
        for action in actions:
            action_experiences = [
                (i, a, f, s)
                for i, a, f, s in self.experiences
                if a.name == action.name
            ]
            if action_experiences:
                success_count = sum(1 for _, _, _, s in action_experiences if s)
                success_rate = success_count / len(action_experiences)
                success_rates.append(success_rate)
        
        if not success_rates:
            return 0.5  # Padrão
        
        # Probabilidade total = produto das probabilidades individuais
        from math import prod
        return prod(success_rates)
    
    def _extract_relations(self, node: Node) -> List[Node]:
        """Extrai relações de um nó."""
        relations = []
        
        if node.kind is NodeKind.REL:
            relations.append(node)
        
        for arg in node.args:
            relations.extend(self._extract_relations(arg))
        
        if node.kind is NodeKind.STRUCT:
            for _, value in node.fields:
                relations.extend(self._extract_relations(value))
        
        return relations
    
    def _extract_relations_from_list(self, nodes: Tuple[Node, ...]) -> List[Node]:
        """Extrai relações de uma lista de nós."""
        relations = []
        for node in nodes:
            relations.extend(self._extract_relations(node))
        return relations


__all__ = ["Action", "Plan", "PlanningSystem"]
