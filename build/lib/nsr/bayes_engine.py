"""
Motor determinístico para inferência Bayesiana discreta.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, Mapping, Sequence, Tuple


@dataclass(frozen=True, slots=True)
class BayesVariable:
    name: str
    values: Tuple[str, ...]
    parents: Tuple[str, ...] = ()


@dataclass(slots=True)
class BayesNetwork:
    """
    Representa uma rede Bayesiana discreta com inferência determinística.
    """

    variables: Dict[str, BayesVariable] = field(default_factory=dict)
    _order: Tuple[str, ...] = field(default_factory=tuple)
    _cpts: Dict[str, Dict[Tuple[Tuple[str, str], ...], Dict[str, float]]] = field(default_factory=dict)

    def add_variable(
        self,
        name: str,
        *,
        values: Sequence[str],
        parents: Sequence[str] | None = None,
    ) -> None:
        if not name:
            raise ValueError("Variable name cannot be empty")
        key = name.strip()
        if key in self.variables:
            raise ValueError(f"Variable '{key}' already registered")
        normalized_values = tuple(dict.fromkeys(v.strip() for v in values if v.strip()))
        if not normalized_values:
            raise ValueError(f"Variable '{key}' requires at least one value")
        normalized_parents = tuple(dict.fromkeys(p.strip() for p in (parents or ()) if p.strip()))
        for parent in normalized_parents:
            if parent == key:
                raise ValueError(f"Variable '{key}' cannot depend on itself")
        variable = BayesVariable(name=key, values=normalized_values, parents=normalized_parents)
        self.variables[key] = variable
        self._order = tuple((*self._order, key))
        self._cpts[key] = {}

    def set_distribution(
        self,
        variable: str,
        *,
        given: Mapping[str, str] | None = None,
        distribution: Mapping[str, float],
    ) -> None:
        var = self._require_variable(variable)
        assignment_key = self._assignment_key(given or {}, var.parents)
        normalized_distribution: Dict[str, float] = {}
        total = 0.0
        for value, prob in distribution.items():
            value_key = value.strip()
            if value_key not in var.values:
                raise ValueError(f"Value '{value_key}' is not valid for variable '{var.name}'")
            if prob < 0.0:
                raise ValueError("Probabilities must be non-negative")
            normalized_distribution[value_key] = float(prob)
            total += float(prob)
        if abs(total - 1.0) > 1e-6:
            raise ValueError(f"Distribution for '{var.name}' does not sum to 1 (total={total})")
        self._cpts[var.name][assignment_key] = normalized_distribution

    def posterior(self, variable: str, evidence: Mapping[str, str] | None = None) -> Dict[str, float]:
        """
        Calcula P(variable | evidence) via enumeração determinística.
        """

        var = self._require_variable(variable)
        evidence_map = {name.strip(): value.strip() for name, value in (evidence or {}).items()}
        for name, value in evidence_map.items():
            target = self._require_variable(name)
            if value not in target.values:
                raise ValueError(f"Value '{value}' is not valid for variable '{name}'")
        results: Dict[str, float] = {}
        for value in var.values:
            extended = dict(evidence_map)
            extended[var.name] = value
            results[value] = self._enumerate_all(self._order, extended)
        total = sum(results.values())
        if total <= 0.0:
            raise ValueError("Posterior could not be normalized (probability mass is zero)")
        return {value: round(prob / total, 6) for value, prob in results.items()}

    def summarize(self) -> Dict[str, object]:
        """
        Devolve estatísticas determinísticas para auditoria.
        """

        edges = sum(len(var.parents) for var in self.variables.values())
        return {
            "variable_count": len(self.variables),
            "edge_count": edges,
            "variables": [
                {
                    "name": var.name,
                    "values": list(var.values),
                    "parents": list(var.parents),
                }
                for var in self.variables.values()
            ],
        }

    # Internals -----------------------------------------------------------------

    def _require_variable(self, name: str) -> BayesVariable:
        key = name.strip()
        if key not in self.variables:
            raise ValueError(f"Unknown variable '{name}'")
        return self.variables[key]

    def _enumerate_all(self, order: Tuple[str, ...], evidence: Dict[str, str]) -> float:
        if not order:
            return 1.0
        first_name, *rest_order = order
        first = self.variables[first_name]
        if first.name in evidence:
            prob = self._probability(first, evidence[first.name], evidence)
            return prob * self._enumerate_all(tuple(rest_order), evidence)
        total = 0.0
        for value in first.values:
            evidence[first.name] = value
            prob = self._probability(first, value, evidence)
            total += prob * self._enumerate_all(tuple(rest_order), evidence)
        evidence.pop(first.name, None)
        return total

    def _probability(self, variable: BayesVariable, value: str, evidence: Mapping[str, str]) -> float:
        distro_map = self._cpts.get(variable.name) or {}
        key = self._assignment_key(evidence, variable.parents)
        distribution = distro_map.get(key)
        if distribution is None:
            raise ValueError(f"Missing CPT entry for '{variable.name}' with parents {dict(key)}")
        prob = distribution.get(value)
        if prob is None:
            raise ValueError(f"Missing probability for value '{value}' in variable '{variable.name}'")
        return prob

    @staticmethod
    def _assignment_key(assignments: Mapping[str, str], parents: Iterable[str]) -> Tuple[Tuple[str, str], ...]:
        key = []
        for parent in parents:
            if parent not in assignments:
                raise ValueError(f"Parent '{parent}' missing from assignment")
            key.append((parent, assignments[parent]))
        if not parents:
            return ()
        return tuple(sorted(key))


__all__ = ["BayesNetwork", "BayesVariable"]
