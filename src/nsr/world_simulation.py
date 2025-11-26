"""
Simulação Interna: Modelo do mundo que pode ser simulado.

Sistema que mantém modelo interno do mundo e simula consequências.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Set, Tuple

from liu import Node, NodeKind, fingerprint


@dataclass(slots=True)
class WorldModel:
    """
    Modelo interno do mundo.
    
    Representa:
    - Estados possíveis
    - Transições entre estados
    - Leis do mundo (regras físicas/lógicas)
    """
    
    # Estados conhecidos
    states: Dict[str, Node] = field(default_factory=dict)
    
    # Transições: (estado, ação) -> estado
    transitions: Dict[Tuple[str, str], str] = field(default_factory=dict)
    
    # Leis do mundo (regras que sempre se aplicam)
    laws: List[Node] = field(default_factory=list)
    
    # Probabilidades de transição
    transition_probs: Dict[Tuple[str, str], float] = field(default_factory=dict)


class WorldSimulator:
    """
    Simula mundo internamente para prever consequências.
    
    Processo:
    1. Mantém modelo do mundo
    2. Simula ações
    3. Prediz consequências
    4. Aprende modelo através de observação
    """
    
    def __init__(self):
        self.model = WorldModel()
        self.observations: List[Tuple[Node, Node, Node]] = []  # (estado, ação, novo_estado)
    
    def observe(self, state: Node, action: Node, new_state: Node) -> None:
        """Observa transição do mundo real."""
        self.observations.append((state, action, new_state))
        self._update_model(state, action, new_state)
    
    def simulate(self, initial_state: Node, action: Node, steps: int = 1) -> Node:
        """
        Simula execução de ação no modelo interno.
        
        Retorna estado previsto após steps.
        """
        current_state = initial_state
        current_key = fingerprint(current_state)
        
        # Adiciona estado ao modelo se não existe
        if current_key not in self.model.states:
            self.model.states[current_key] = current_state
        
        for _ in range(steps):
            action_key = fingerprint(action)
            transition_key = (current_key, action_key)
            
            # Verifica se conhece transição
            if transition_key in self.model.transitions:
                new_key = self.model.transitions[transition_key]
                current_state = self.model.states.get(new_key, current_state)
                current_key = new_key
            else:
                # Prediz baseado em transições similares
                predicted = self._predict_transition(current_state, action)
                if predicted:
                    current_state = predicted
                    current_key = fingerprint(current_state)
                # Se não consegue prever, mantém estado atual
        
        return current_state
    
    def predict_consequences(
        self, initial_state: Node, actions: List[Node], steps: int = 10
    ) -> List[Node]:
        """
        Prediz consequências de uma sequência de ações.
        
        Retorna lista de estados previstos.
        """
        states = [initial_state]
        current = initial_state
        
        for action in actions:
            if len(states) >= steps:
                break
            
            next_state = self.simulate(current, action, steps=1)
            states.append(next_state)
            current = next_state
        
        return states
    
    def learn_model(self) -> None:
        """Aprende modelo do mundo a partir de observações."""
        
        # Agrupa observações por ação
        action_transitions: Dict[str, List[Tuple[str, str]]] = defaultdict(list)
        
        for state, action, new_state in self.observations:
            state_key = fingerprint(state)
            action_key = fingerprint(action)
            new_state_key = fingerprint(new_state)
            
            action_transitions[action_key].append((state_key, new_state_key))
        
        # Aprende transições mais comuns
        for action_key, transitions in action_transitions.items():
            # Conta transições
            transition_counts: Dict[Tuple[str, str], int] = defaultdict(int)
            for trans in transitions:
                transition_counts[trans] += 1
            
            # Seleciona transição mais comum
            if transition_counts:
                most_common = max(transition_counts.items(), key=lambda x: x[1])
                transition_key = (most_common[0][0], action_key)
                self.model.transitions[transition_key] = most_common[0][1]
                
                # Probabilidade = frequência
                total = sum(transition_counts.values())
                prob = most_common[1] / total
                self.model.transition_probs[transition_key] = prob
    
    def _update_model(self, state: Node, action: Node, new_state: Node) -> None:
        """Atualiza modelo com nova observação."""
        state_key = fingerprint(state)
        action_key = fingerprint(action)
        new_state_key = fingerprint(new_state)
        
        # Adiciona estados
        self.model.states[state_key] = state
        self.model.states[new_state_key] = new_state
        
        # Atualiza transição
        transition_key = (state_key, action_key)
        self.model.transitions[transition_key] = new_state_key
        
        # Atualiza probabilidade
        # Simplificação: assume 1.0 se única observação
        if transition_key not in self.model.transition_probs:
            self.model.transition_probs[transition_key] = 1.0
    
    def _predict_transition(self, state: Node, action: Node) -> Node | None:
        """Prediz transição baseado em transições similares."""
        # Simplificação: retorna None (não prediz)
        # Em produção, usaria similaridade estrutural
        return None


__all__ = ["WorldModel", "WorldSimulator"]
