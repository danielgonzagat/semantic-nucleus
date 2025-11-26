"""
Motor determinístico para cadeias de Markov/HMM discretas.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, Mapping, Sequence, Tuple


def _normalize(probabilities: Dict[str, float]) -> Dict[str, float]:
    total = sum(probabilities.values())
    if total <= 0.0:
        raise ValueError("probability mass must be > 0")
    return {state: round(value / total, 6) for state, value in probabilities.items()}


@dataclass()
class MarkovModel:
    """
    Cadeia de Markov/HMM discreta com inferência determinística (algoritmo forward).
    """

    states: Tuple[str, ...]
    transitions: Dict[str, Dict[str, float]] = field(default_factory=dict)
    emissions: Dict[str, Dict[str, float]] = field(default_factory=dict)
    initial: Dict[str, float] = field(default_factory=dict)

    @staticmethod
    def from_payload(payload: Mapping[str, object]) -> "MarkovModel":
        states = tuple(dict.fromkeys(str(state).strip() for state in payload.get("states", []) if str(state).strip()))
        if not states:
            raise ValueError("states list cannot be empty")
        transitions = _parse_transition_matrix(states, payload.get("transitions"))
        emissions = _parse_emissions(states, payload.get("emissions"))
        initial = _parse_distribution(states, payload.get("initial"))
        return MarkovModel(states=states, transitions=transitions, emissions=emissions, initial=initial)

    def forward(self, observations: Sequence[str] | None = None) -> Tuple[Dict[str, float], Tuple[Dict[str, float], ...], float]:
        """
        Executa o algoritmo forward determinístico e retorna:
            (distribuição final, histórico de distribuições, verossimilhança total)
        """

        obs_sequence = tuple(str(obs).strip() for obs in (observations or ()))
        history: list[Dict[str, float]] = []
        current = dict(self.initial)
        self._ensure_distribution(current)
        likelihood = 1.0
        for observation in obs_sequence:
            propagated = self._propagate(current)
            if observation:
                propagated = self._apply_emission(propagated, observation)
            history.append(dict(propagated))
            current = propagated
            likelihood *= sum(propagated.values())
        return current, tuple(history), round(likelihood, 6)

    def summarize(self) -> Dict[str, object]:
        return {
            "state_count": len(self.states),
            "states": list(self.states),
            "transition_edges": sum(len(row) for row in self.transitions.values()),
            "emission_symbols": sorted({symbol for table in self.emissions.values() for symbol in table}),
        }

    def _propagate(self, distribution: Mapping[str, float]) -> Dict[str, float]:
        next_distribution: Dict[str, float] = {state: 0.0 for state in self.states}
        for from_state, prob in distribution.items():
            for to_state, transition_prob in self.transitions[from_state].items():
                next_distribution[to_state] += prob * transition_prob
        return _normalize(next_distribution)

    def _apply_emission(self, distribution: Mapping[str, float], observation: str) -> Dict[str, float]:
        adjusted = {}
        for state, prob in distribution.items():
            emission_table = self.emissions.get(state)
            weight = emission_table.get(observation) if emission_table else 1.0
            if weight is None:
                raise ValueError(f"Emission for '{observation}' missing in state '{state}'")
            adjusted[state] = prob * weight
        return _normalize(adjusted)

    def _ensure_distribution(self, distribution: Mapping[str, float]) -> None:
        if set(distribution.keys()) != set(self.states):
            raise ValueError("distribution must reference all states")
        if abs(sum(distribution.values()) - 1.0) > 1e-6:
            raise ValueError("distribution must sum to 1")


def _parse_transition_matrix(states: Iterable[str], entries: object) -> Dict[str, Dict[str, float]]:
    transitions: Dict[str, Dict[str, float]] = {}
    if not isinstance(entries, Sequence):
        raise ValueError("transitions must be a list")
    for entry in entries:
        if not isinstance(entry, Mapping):
            raise ValueError("transition entry must be an object")
        source = str(entry.get("from", "")).strip()
        if source not in states:
            raise ValueError(f"transition source '{source}' not declared")
        distribution = _parse_distribution(states, entry.get("to"))
        transitions[source] = distribution
    if set(transitions.keys()) != set(states):
        raise ValueError("transition matrix must define all states")
    return transitions


def _parse_emissions(states: Iterable[str], entries: object) -> Dict[str, Dict[str, float]]:
    emissions: Dict[str, Dict[str, float]] = {state: {} for state in states}
    if entries is None:
        return emissions
    if not isinstance(entries, Sequence):
        raise ValueError("emissions must be a list")
    for entry in entries:
        if not isinstance(entry, Mapping):
            raise ValueError("emission entry must be an object")
        state = str(entry.get("state", "")).strip()
        if state not in emissions:
            raise ValueError(f"emission state '{state}' not declared")
        symbols = entry.get("symbols") or {}
        if not isinstance(symbols, Mapping):
            raise ValueError("emission symbols must be a mapping")
        normalized = _normalize({str(symbol).strip(): float(prob) for symbol, prob in symbols.items()})
        emissions[state] = normalized
    return emissions


def _parse_distribution(states: Iterable[str], distribution: object) -> Dict[str, float]:
    if not isinstance(distribution, Mapping):
        raise ValueError("distribution must be an object")
    normalized = {}
    for state in states:
        if state not in distribution:
            raise ValueError(f"state '{state}' missing from distribution")
        value = float(distribution[state])
        if value < 0.0:
            raise ValueError("distribution values must be >= 0")
        normalized[state] = value
    return _normalize(normalized)


__all__ = ["MarkovModel"]
