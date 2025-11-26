"""
Markov bridge – interpreta comandos MARKOV {json} para cadeias determinísticas/HMM.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Mapping, Tuple

from liu import Node, entity, list_node, number, struct as liu_struct, text as liu_text

from .markov_engine import MarkovModel


@dataclass(frozen=True)
class MarkovHook:
    struct_node: Node
    answer_node: Node
    context_nodes: Tuple[Node, ...]
    quality: float
    trace_label: str


def maybe_route_markov(text: str) -> MarkovHook | None:
    trimmed = (text or "").strip()
    if not trimmed:
        return None
    prefix, _, remainder = trimmed.partition(" ")
    if prefix.upper() != "MARKOV":
        return None
    payload_text = remainder.strip()
    if not payload_text:
        return None
    try:
        payload = json.loads(payload_text)
    except json.JSONDecodeError:
        return None
    try:
        model = MarkovModel.from_payload(payload)
        observations = tuple(str(obs).strip() for obs in payload.get("observations", []) if str(obs).strip())
        final_distribution, history, likelihood = model.forward(observations)
    except ValueError:
        return None
    struct_node = liu_struct(
        tag=entity("markov_input"),
        observation_count=number(len(observations)),
    )
    answer_node, forward_node = _build_answer(model.states, final_distribution, likelihood)
    context_nodes = (
        _model_context(model),
        _observation_context(observations),
        forward_node,
    )
    return MarkovHook(
        struct_node=struct_node,
        answer_node=answer_node,
        context_nodes=context_nodes,
        quality=0.91,
        trace_label="STAT[MARKOV_FORWARD]",
    )


def _build_answer(states: Tuple[str, ...], distribution: Mapping[str, float], likelihood: float) -> tuple[Node, Node]:
    entries = [
        liu_struct(tag=entity("markov_state"), name=entity(state), probability=number(prob))
        for state, prob in distribution.items()
    ]
    description = ", ".join(f"{state}={prob:.3f}" for state, prob in distribution.items())
    answer_node = liu_struct(
        tag=entity("markov_answer"),
        states=list_node(entries),
        likelihood=number(likelihood),
        answer=liu_text(f"forward(states) → {description}"),
    )
    forward_node = liu_struct(
        tag=entity("markov_distribution"),
        states=list_node(entries),
        likelihood=number(likelihood),
    )
    return answer_node, forward_node


def _model_context(model: MarkovModel) -> Node:
    summary = model.summarize()
    state_nodes = [entity(state) for state in summary["states"]]
    return liu_struct(
        tag=entity("markov_model"),
        state_count=number(summary["state_count"]),
        states=list_node(state_nodes),
        transition_edges=number(summary["transition_edges"]),
        emission_symbols=list_node(entity(sym) for sym in summary["emission_symbols"]),
    )


def _observation_context(observations: Tuple[str, ...]) -> Node:
    if not observations:
        return liu_struct(tag=entity("markov_observations"), entries=list_node(()))
    entries = [liu_struct(tag=entity("markov_observation"), index=number(idx), symbol=entity(symbol)) for idx, symbol in enumerate(observations)]
    return liu_struct(
        tag=entity("markov_observations"),
        entries=list_node(entries),
    )


__all__ = ["MarkovHook", "maybe_route_markov"]
