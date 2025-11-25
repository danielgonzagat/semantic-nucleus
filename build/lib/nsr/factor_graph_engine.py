"""
Belief Propagation determinístico para grafos fatoriais discretos.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Mapping, Tuple


@dataclass(frozen=True, slots=True)
class FactorVariable:
    name: str
    values: Tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Factor:
    name: str
    variables: Tuple[str, ...]
    table: Dict[Tuple[str, ...], float]


@dataclass(slots=True)
class FactorGraph:
    variables: Dict[str, FactorVariable] = field(default_factory=dict)
    factors: Dict[str, Factor] = field(default_factory=dict)

    @staticmethod
    def from_payload(payload: Mapping[str, object]) -> FactorGraph:
        variables = {}
        factors = {}
        for var_def in payload.get("variables", []):
            name = str(var_def["name"]).strip()
            values = tuple(dict.fromkeys(str(value).strip() for value in var_def["values"]))
            variables[name] = FactorVariable(name=name, values=values)
        for factor_def in payload.get("factors", []):
            name = str(factor_def["name"]).strip()
            var_names = tuple(str(var).strip() for var in factor_def["variables"])
            table_entries = {}
            for row in factor_def["table"]:
                assignment = tuple(str(row["assignment"][var]).strip() for var in var_names)
                weight = float(row["value"])
                table_entries[assignment] = weight
            factors[name] = Factor(name=name, variables=var_names, table=table_entries)
        graph = FactorGraph(variables=variables, factors=factors)
        graph._validate()
        return graph

    def _validate(self) -> None:
        for factor in self.factors.values():
            for var_name in factor.variables:
                if var_name not in self.variables:
                    raise ValueError(f"factor '{factor.name}' references unknown variable '{var_name}'")
            for assignment in factor.table:
                if len(assignment) != len(factor.variables):
                    raise ValueError(f"factor '{factor.name}' assignment length mismatch")

    def belief_propagation(
        self,
        *,
        max_iters: int = 20,
        damping: float = 0.0,
    ) -> Dict[str, Dict[str, float]]:
        messages = self._initialize_messages()
        for _ in range(max_iters):
            new_messages = self._iterate_messages(messages, damping)
            if self._messages_converged(messages, new_messages):
                messages = new_messages
                break
            messages = new_messages
        return self._compute_marginals(messages)

    def _variable_neighbors(self, variable: str) -> Tuple[str, ...]:
        return tuple(
            factor.name
            for factor in self.factors.values()
            if variable in factor.variables
        )

    def _factor_neighbors(self, factor_name: str) -> Tuple[str, ...]:
        factor = self.factors[factor_name]
        return factor.variables

    def _initialize_messages(self) -> Dict[Tuple[str, str], Dict[str, float]]:
        messages: Dict[Tuple[str, str], Dict[str, float]] = {}
        for variable in self.variables:
            neighbors = self._variable_neighbors(variable)
            for factor in neighbors:
                messages[(variable, factor)] = {
                    value: 1.0 / len(self.variables[variable].values)
                    for value in self.variables[variable].values
                }
                messages[(factor, variable)] = {
                    value: 1.0 / len(self.variables[variable].values)
                    for value in self.variables[variable].values
                }
        return messages

    def _iterate_messages(
        self,
        messages: Dict[Tuple[str, str], Dict[str, float]],
        damping: float,
    ) -> Dict[Tuple[str, str], Dict[str, float]]:
        new_messages = dict(messages)
        for factor_name, factor in self.factors.items():
            for target_variable in factor.variables:
                incoming = [
                    (neighbor, messages[(neighbor, factor_name)])
                    for neighbor in factor.variables
                    if neighbor != target_variable
                ]
                table = factor.table
                variable_values = self.variables[target_variable].values
                updated = {}
                for target_value in variable_values:
                    total = 0.0
                    for assignment, weight in table.items():
                        if assignment[factor.variables.index(target_variable)] != target_value:
                            continue
                        product = weight
                        for neighbor_name, neighbor_message in incoming:
                            neighbor_value = assignment[factor.variables.index(neighbor_name)]
                            product *= neighbor_message[neighbor_value]
                        total += product
                    updated[target_value] = total
                new_messages[(factor_name, target_variable)] = _normalize(updated, damping, messages[(factor_name, target_variable)])
        for variable_name, variable in self.variables.items():
            neighbors = self._variable_neighbors(variable_name)
            for factor_name in neighbors:
                product = {value: 1.0 for value in variable.values}
                for other_factor in neighbors:
                    if other_factor == factor_name:
                        continue
                    incoming = new_messages[(other_factor, variable_name)]
                    for value in variable.values:
                        product[value] *= incoming[value]
                new_messages[(variable_name, factor_name)] = _normalize(product, damping, messages[(variable_name, factor_name)])
        return new_messages

    def _messages_converged(
        self,
        old: Dict[Tuple[str, str], Dict[str, float]],
        new: Dict[Tuple[str, str], Dict[str, float]],
        threshold: float = 1e-6,
    ) -> bool:
        for key in old:
            for value in old[key]:
                if abs(old[key][value] - new[key][value]) > threshold:
                    return False
        return True

    def _compute_marginals(self, messages: Dict[Tuple[str, str], Dict[str, float]]) -> Dict[str, Dict[str, float]]:
        marginals: Dict[str, Dict[str, float]] = {}
        for variable_name, variable in self.variables.items():
            product = {value: 1.0 for value in variable.values}
            neighbors = self._variable_neighbors(variable_name)
            for factor_name in neighbors:
                incoming = messages[(factor_name, variable_name)]
                for value in variable.values:
                    product[value] *= incoming[value]
            marginals[variable_name] = _normalize(product)
        return marginals


def _normalize(
    distribution: Mapping[str, float],
    damping: float = 0.0,
    previous: Mapping[str, float] | None = None,
) -> Dict[str, float]:
    total = sum(distribution.values())
    if total <= 0.0:
        raise ValueError("distribution mass is zero or negative")
    normalized = {state: value / total for state, value in distribution.items()}
    if previous is not None and damping > 0.0:
        return {
            state: (1 - damping) * normalized[state] + damping * previous[state]
            for state in normalized
        }
    return normalized


__all__ = ["FactorGraph", "FactorVariable", "Factor"]
