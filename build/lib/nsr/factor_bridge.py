"""
Factor bridge – executa belief propagation determinístico via FACTOR {json}.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Tuple

from liu import Node, entity, list_node, number, struct as liu_struct, text as liu_text

from .factor_graph_engine import FactorGraph


@dataclass(frozen=True, slots=True)
class FactorHook:
    struct_node: Node
    answer_node: Node
    context_nodes: Tuple[Node, ...]
    quality: float
    trace_label: str


def maybe_route_factor(text: str) -> FactorHook | None:
    trimmed = (text or "").strip()
    if not trimmed:
        return None
    prefix, _, remainder = trimmed.partition(" ")
    if prefix.upper() != "FACTOR":
        return None
    payload_text = remainder.strip()
    if not payload_text:
        return None
    try:
        payload = json.loads(payload_text)
    except json.JSONDecodeError:
        return None
    try:
        graph = FactorGraph.from_payload(payload)
        marginals = graph.belief_propagation(
            max_iters=int(payload.get("max_iters", 20)),
            damping=float(payload.get("damping", 0.0)),
        )
    except (ValueError, TypeError):
        return None
    struct_node = liu_struct(
        tag=entity("factor_input"),
        variable_count=number(len(graph.variables)),
        factor_count=number(len(graph.factors)),
    )
    answer_node = _build_answer(marginals)
    context_nodes = (_build_graph_summary(graph), _build_marginals(marginals))
    return FactorHook(
        struct_node=struct_node,
        answer_node=answer_node,
        context_nodes=context_nodes,
        quality=0.9,
        trace_label="STAT[FACTOR_BP]",
    )


def _build_answer(marginals: dict[str, dict[str, float]]) -> Node:
    best = []
    for var, distribution in marginals.items():
        state = max(distribution.items(), key=lambda item: item[1])
        best.append(f"{var}={state[0]}({state[1]:.3f})")
    description = ", ".join(best)
    return liu_struct(
        tag=entity("factor_answer"),
        answer=liu_text(f"Belief Propagation → {description}"),
    )


def _build_graph_summary(graph: FactorGraph) -> Node:
    var_nodes = [
        liu_struct(
            tag=entity("factor_variable"),
            name=entity(name),
            values=list_node(entity(value) for value in variable.values),
        )
        for name, variable in graph.variables.items()
    ]
    factor_nodes = [
        liu_struct(
            tag=entity("factor_definition"),
            name=entity(factor.name),
            variables=list_node(entity(var) for var in factor.variables),
        )
        for factor in graph.factors.values()
    ]
    return liu_struct(
        tag=entity("factor_graph"),
        variables=list_node(var_nodes),
        factors=list_node(factor_nodes),
    )


def _build_marginals(marginals: dict[str, dict[str, float]]) -> Node:
    entries = [
        liu_struct(
            tag=entity("factor_marginal"),
            variable=entity(var),
            distribution=list_node(
                liu_struct(state=entity(state), probability=number(prob))
                for state, prob in distribution.items()
            ),
        )
        for var, distribution in marginals.items()
    ]
    return liu_struct(tag=entity("factor_marginals"), entries=list_node(entries))


__all__ = ["FactorHook", "maybe_route_factor"]
