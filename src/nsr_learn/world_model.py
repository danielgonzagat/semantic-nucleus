"""
World Model Discreto: Simular Consequências de Ações.

Um World Model permite ao agente "imaginar" o que aconteceria
se tomasse certas ações, SEM realmente executá-las.

LLMs fazem isso implicitamente através de previsão next-token.
Nós fazemos EXPLICITAMENTE através de:

1. ESTADOS: Representações simbólicas do mundo
2. TRANSIÇÕES: Regras que descrevem como ações mudam estados
3. SIMULAÇÃO: Execução mental de sequências de ações
4. PLANEJAMENTO: Busca de sequências que alcançam objetivos

Isso permite:
- Raciocínio sobre consequências
- Planejamento de múltiplos passos
- Aprendizado por simulação
- Transferência para novos cenários

Inspiração: PDDL, STRIPS, Situational Calculus
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, FrozenSet, Iterator, List, Mapping, Sequence, Set, Tuple
import heapq


@dataclass(frozen=True)
class Fluent:
    """
    Um fluent é uma proposição que pode mudar ao longo do tempo.
    
    Exemplo: at(robot, room1), holding(robot, box), door_open(door1)
    """
    
    predicate: str
    args: Tuple[str, ...]
    
    def __str__(self) -> str:
        args_str = ", ".join(self.args)
        return f"{self.predicate}({args_str})"
    
    def ground(self, bindings: Mapping[str, str]) -> "Fluent":
        """Substitui variáveis por valores."""
        new_args = tuple(
            bindings.get(arg, arg) if arg.startswith("?") else arg
            for arg in self.args
        )
        return Fluent(self.predicate, new_args)


@dataclass(frozen=True)
class State:
    """
    Estado do mundo = conjunto de fluents verdadeiros.
    
    Closed World Assumption: o que não está presente é falso.
    """
    
    fluents: FrozenSet[Fluent]
    
    def holds(self, fluent: Fluent) -> bool:
        """Verifica se um fluent é verdadeiro."""
        return fluent in self.fluents
    
    def satisfies(self, conditions: FrozenSet[Fluent]) -> bool:
        """Verifica se todas as condições são satisfeitas."""
        return conditions.issubset(self.fluents)
    
    def apply(
        self,
        add: FrozenSet[Fluent],
        delete: FrozenSet[Fluent],
    ) -> "State":
        """Aplica efeitos e retorna novo estado."""
        new_fluents = (self.fluents - delete) | add
        return State(new_fluents)
    
    def difference(self, other: "State") -> Set[Fluent]:
        """Retorna fluents presentes aqui mas não no outro."""
        return self.fluents - other.fluents
    
    def __str__(self) -> str:
        fluents_str = ", ".join(sorted(str(f) for f in self.fluents))
        return f"{{{fluents_str}}}"
    
    def __hash__(self) -> int:
        return hash(self.fluents)


@dataclass(frozen=True)
class Action:
    """
    Uma ação que pode ser executada.
    
    Estrutura STRIPS:
    - Precondições: o que deve ser verdade para executar
    - Efeitos positivos (add): o que se torna verdade
    - Efeitos negativos (delete): o que deixa de ser verdade
    """
    
    name: str
    parameters: Tuple[str, ...]  # Variáveis como ?x, ?y
    preconditions: FrozenSet[Fluent]
    add_effects: FrozenSet[Fluent]
    delete_effects: FrozenSet[Fluent]
    cost: float = 1.0
    
    def is_applicable(self, state: State) -> bool:
        """Verifica se a ação pode ser executada no estado."""
        return state.satisfies(self.preconditions)
    
    def apply(self, state: State) -> State:
        """Aplica a ação e retorna novo estado."""
        return state.apply(self.add_effects, self.delete_effects)
    
    def ground(self, bindings: Mapping[str, str]) -> "Action":
        """Substitui variáveis por objetos específicos."""
        new_name = f"{self.name}({', '.join(bindings.get(p, p) for p in self.parameters)})"
        
        return Action(
            name=new_name,
            parameters=(),
            preconditions=frozenset(f.ground(bindings) for f in self.preconditions),
            add_effects=frozenset(f.ground(bindings) for f in self.add_effects),
            delete_effects=frozenset(f.ground(bindings) for f in self.delete_effects),
            cost=self.cost,
        )
    
    def __str__(self) -> str:
        params = ", ".join(self.parameters)
        return f"{self.name}({params})"


@dataclass
class TransitionRule:
    """
    Regra de transição aprendida de observações.
    
    Quando: precondições
    Se: ação
    Então: efeitos
    Com probabilidade: confidence
    """
    
    action_pattern: str
    preconditions: Set[str]  # Padrões de fluent
    add_effects: Set[str]
    delete_effects: Set[str]
    support: int = 0
    confidence: float = 1.0
    
    def matches(self, action_name: str, state: State) -> bool:
        """Verifica se a regra se aplica."""
        if self.action_pattern not in action_name:
            return False
        
        state_strs = {str(f) for f in state.fluents}
        return all(any(p in s for s in state_strs) for p in self.preconditions)


@dataclass
class Plan:
    """Um plano = sequência de ações."""
    
    actions: List[Action] = field(default_factory=list)
    
    @property
    def cost(self) -> float:
        return sum(a.cost for a in self.actions)
    
    @property
    def length(self) -> int:
        return len(self.actions)
    
    def __str__(self) -> str:
        return " → ".join(a.name for a in self.actions)


class WorldModel:
    """
    Modelo de mundo discreto.
    
    Permite:
    1. Definir estados e ações
    2. Simular execução de ações
    3. Aprender regras de transição
    4. Planejar para alcançar objetivos
    """
    
    def __init__(self):
        self.actions: Dict[str, Action] = {}
        self.objects: Dict[str, Set[str]] = defaultdict(set)  # type → objects
        self.learned_rules: List[TransitionRule] = []
        
        # Histórico para aprendizado
        self.transition_history: List[Tuple[State, str, State]] = []
    
    def add_action_schema(self, action: Action) -> None:
        """Adiciona um esquema de ação."""
        self.actions[action.name] = action
    
    def add_object(self, obj: str, obj_type: str) -> None:
        """Adiciona um objeto ao mundo."""
        self.objects[obj_type].add(obj)
    
    def simulate(
        self,
        initial_state: State,
        actions: Sequence[Action],
    ) -> List[State]:
        """
        Simula uma sequência de ações.
        
        Retorna a trajetória de estados.
        """
        trajectory = [initial_state]
        current = initial_state
        
        for action in actions:
            if not action.is_applicable(current):
                break
            
            current = action.apply(current)
            trajectory.append(current)
        
        return trajectory
    
    def predict_next_state(
        self,
        state: State,
        action: Action,
    ) -> State | None:
        """Prediz o próximo estado após uma ação."""
        if not action.is_applicable(state):
            return None
        
        return action.apply(state)
    
    def get_applicable_actions(
        self,
        state: State,
    ) -> List[Action]:
        """Retorna todas as ações aplicáveis no estado."""
        applicable = []
        
        for action_schema in self.actions.values():
            # Gera todas as instanciações possíveis
            grounded = self._ground_action(action_schema, state)
            applicable.extend(a for a in grounded if a.is_applicable(state))
        
        return applicable
    
    def plan(
        self,
        initial_state: State,
        goal: FrozenSet[Fluent],
        max_depth: int = 20,
    ) -> Plan | None:
        """
        Planeja uma sequência de ações para alcançar o objetivo.
        
        Usa A* com heurística de contagem de objetivos não satisfeitos.
        """
        if initial_state.satisfies(goal):
            return Plan()
        
        # Priority queue: (custo + heurística, custo, state, actions)
        start = (self._heuristic(initial_state, goal), 0.0, initial_state, [])
        frontier = [start]
        visited: Set[State] = set()
        
        while frontier:
            _, cost, state, actions = heapq.heappop(frontier)
            
            if state in visited:
                continue
            
            visited.add(state)
            
            if state.satisfies(goal):
                return Plan(actions=actions)
            
            if len(actions) >= max_depth:
                continue
            
            for action in self.get_applicable_actions(state):
                next_state = action.apply(state)
                
                if next_state in visited:
                    continue
                
                new_cost = cost + action.cost
                priority = new_cost + self._heuristic(next_state, goal)
                new_actions = actions + [action]
                
                heapq.heappush(frontier, (priority, new_cost, next_state, new_actions))
        
        return None
    
    def learn_from_observation(
        self,
        before: State,
        action_name: str,
        after: State,
    ) -> TransitionRule:
        """
        Aprende uma regra de transição de uma observação.
        """
        self.transition_history.append((before, action_name, after))
        
        # Identifica efeitos
        added = after.difference(before)
        deleted = before.difference(after)
        
        # Cria regra
        rule = TransitionRule(
            action_pattern=action_name,
            preconditions={str(f) for f in before.fluents},
            add_effects={str(f) for f in added},
            delete_effects={str(f) for f in deleted},
            support=1,
        )
        
        # Verifica se já existe regra similar
        for existing in self.learned_rules:
            if (existing.action_pattern == rule.action_pattern and
                existing.add_effects == rule.add_effects):
                existing.support += 1
                existing.confidence = existing.support / len(self.transition_history)
                return existing
        
        self.learned_rules.append(rule)
        return rule
    
    def predict_with_learned_rules(
        self,
        state: State,
        action_name: str,
    ) -> State | None:
        """
        Prediz próximo estado usando regras aprendidas.
        
        Útil quando não temos o modelo completo.
        """
        best_rule = None
        best_confidence = 0.0
        
        for rule in self.learned_rules:
            if rule.matches(action_name, state) and rule.confidence > best_confidence:
                best_rule = rule
                best_confidence = rule.confidence
        
        if best_rule is None:
            return None
        
        # Aplica efeitos
        add_fluents = set()
        delete_fluents = set()
        
        for f in state.fluents:
            f_str = str(f)
            if any(d in f_str for d in best_rule.delete_effects):
                delete_fluents.add(f)
        
        # Adiciona efeitos (parse simplificado)
        for add_str in best_rule.add_effects:
            # Tenta criar fluent do string
            if "(" in add_str:
                pred = add_str.split("(")[0]
                args = add_str.split("(")[1].rstrip(")").split(", ")
                add_fluents.add(Fluent(pred, tuple(args)))
        
        return state.apply(frozenset(add_fluents), frozenset(delete_fluents))
    
    def _ground_action(
        self,
        action: Action,
        state: State,
    ) -> List[Action]:
        """Gera todas as instanciações de uma ação."""
        if not action.parameters:
            return [action]
        
        # Simplificação: usa objetos de todos os tipos
        all_objects = set()
        for objs in self.objects.values():
            all_objects.update(objs)
        
        # Extrai objetos do estado também
        for fluent in state.fluents:
            all_objects.update(fluent.args)
        
        if not all_objects:
            return []
        
        # Gera combinações
        from itertools import product
        
        grounded = []
        object_list = list(all_objects)
        
        for combo in product(object_list, repeat=len(action.parameters)):
            bindings = {param: obj for param, obj in zip(action.parameters, combo)}
            grounded.append(action.ground(bindings))
        
        return grounded[:100]  # Limita para performance
    
    def _heuristic(self, state: State, goal: FrozenSet[Fluent]) -> float:
        """Heurística: conta objetivos não satisfeitos."""
        unsatisfied = sum(1 for g in goal if g not in state.fluents)
        return float(unsatisfied)


class MentalSimulator:
    """
    Simulador mental para "imaginar" cenários.
    
    Permite ao agente responder perguntas como:
    - "O que aconteceria se eu fizesse X?"
    - "Quantos passos para alcançar Y?"
    - "Qual é o melhor caminho para Z?"
    """
    
    def __init__(self, world_model: WorldModel):
        self.model = world_model
        self.simulation_cache: Dict[Tuple[State, str], State] = {}
    
    def what_if(
        self,
        state: State,
        action: Action,
    ) -> Dict[str, Any]:
        """
        Responde "o que aconteceria se...?"
        """
        if not action.is_applicable(state):
            return {
                "possible": False,
                "reason": "Ação não aplicável",
                "preconditions_missing": [
                    str(p) for p in action.preconditions
                    if p not in state.fluents
                ],
            }
        
        next_state = action.apply(state)
        
        return {
            "possible": True,
            "result_state": next_state,
            "added": [str(f) for f in action.add_effects],
            "removed": [str(f) for f in action.delete_effects],
        }
    
    def can_reach(
        self,
        from_state: State,
        goal: FrozenSet[Fluent],
        max_steps: int = 10,
    ) -> Dict[str, Any]:
        """
        Verifica se é possível alcançar um objetivo.
        """
        plan = self.model.plan(from_state, goal, max_depth=max_steps)
        
        if plan is None:
            return {
                "reachable": False,
                "reason": f"Não encontrou plano em {max_steps} passos",
            }
        
        return {
            "reachable": True,
            "steps": plan.length,
            "plan": str(plan),
            "cost": plan.cost,
        }
    
    def simulate_trajectory(
        self,
        start: State,
        actions: List[Action],
        explain: bool = False,
    ) -> Dict[str, Any]:
        """
        Simula e explica uma trajetória.
        """
        trajectory = self.model.simulate(start, actions)
        
        result = {
            "success": len(trajectory) == len(actions) + 1,
            "steps_completed": len(trajectory) - 1,
            "final_state": trajectory[-1],
        }
        
        if explain:
            explanations = []
            for i, (state, action) in enumerate(zip(trajectory[:-1], actions)):
                explanations.append({
                    "step": i + 1,
                    "action": action.name,
                    "state_before": str(state),
                    "state_after": str(trajectory[i + 1]),
                })
            result["explanations"] = explanations
        
        return result


# Domínio de exemplo: Blocks World
def create_blocks_world() -> WorldModel:
    """Cria um mundo de blocos clássico."""
    model = WorldModel()
    
    # Ação: pegar bloco da mesa
    pickup = Action(
        name="pickup",
        parameters=("?b",),
        preconditions=frozenset([
            Fluent("on_table", ("?b",)),
            Fluent("clear", ("?b",)),
            Fluent("arm_empty", ()),
        ]),
        add_effects=frozenset([
            Fluent("holding", ("?b",)),
        ]),
        delete_effects=frozenset([
            Fluent("on_table", ("?b",)),
            Fluent("arm_empty", ()),
        ]),
    )
    
    # Ação: colocar bloco na mesa
    putdown = Action(
        name="putdown",
        parameters=("?b",),
        preconditions=frozenset([
            Fluent("holding", ("?b",)),
        ]),
        add_effects=frozenset([
            Fluent("on_table", ("?b",)),
            Fluent("arm_empty", ()),
            Fluent("clear", ("?b",)),
        ]),
        delete_effects=frozenset([
            Fluent("holding", ("?b",)),
        ]),
    )
    
    # Ação: empilhar bloco sobre outro
    stack = Action(
        name="stack",
        parameters=("?b1", "?b2"),
        preconditions=frozenset([
            Fluent("holding", ("?b1",)),
            Fluent("clear", ("?b2",)),
        ]),
        add_effects=frozenset([
            Fluent("on", ("?b1", "?b2")),
            Fluent("arm_empty", ()),
            Fluent("clear", ("?b1",)),
        ]),
        delete_effects=frozenset([
            Fluent("holding", ("?b1",)),
            Fluent("clear", ("?b2",)),
        ]),
    )
    
    # Ação: desempilhar bloco
    unstack = Action(
        name="unstack",
        parameters=("?b1", "?b2"),
        preconditions=frozenset([
            Fluent("on", ("?b1", "?b2")),
            Fluent("clear", ("?b1",)),
            Fluent("arm_empty", ()),
        ]),
        add_effects=frozenset([
            Fluent("holding", ("?b1",)),
            Fluent("clear", ("?b2",)),
        ]),
        delete_effects=frozenset([
            Fluent("on", ("?b1", "?b2")),
            Fluent("arm_empty", ()),
            Fluent("clear", ("?b1",)),
        ]),
    )
    
    model.add_action_schema(pickup)
    model.add_action_schema(putdown)
    model.add_action_schema(stack)
    model.add_action_schema(unstack)
    
    return model


__all__ = [
    "Fluent",
    "State",
    "Action",
    "TransitionRule",
    "Plan",
    "WorldModel",
    "MentalSimulator",
    "create_blocks_world",
]
