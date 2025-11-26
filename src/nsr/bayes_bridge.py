"""
Bayes bridge – interpreta comandos BAYES {json} e executa inferência simbólica.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Mapping, Tuple

from liu import Node, entity, list_node, number, struct as liu_struct, text as liu_text

from .bayes_engine import BayesNetwork


@dataclass(frozen=True)
class BayesHook:
    struct_node: Node
    answer_node: Node
    context_nodes: Tuple[Node, ...]
    quality: float
    trace_label: str


def maybe_route_bayes(text: str) -> BayesHook | None:
    trimmed = (text or "").strip()
    if not trimmed:
        return None
    prefix, _, remainder = trimmed.partition(" ")
    if prefix.upper() != "BAYES":
        return None
    payload_text = remainder.strip()
    if not payload_text:
        return None
    try:
        payload = json.loads(payload_text)
    except json.JSONDecodeError:
        return None
    try:
        network, query, evidence, posterior = _execute_payload(payload)
    except ValueError:
        return None
    struct_node = liu_struct(
        tag=entity("bayes_input"),
        query=entity(query),
        evidence_count=number(len(evidence)),
    )
    answer_node, posterior_node = _build_answer(query, posterior)
    context_nodes = (
        _network_context(network),
        _evidence_context(evidence),
        posterior_node,
    )
    return BayesHook(
        struct_node=struct_node,
        answer_node=answer_node,
        context_nodes=context_nodes,
        quality=0.92,
        trace_label="STAT[BAYES_QUERY]",
    )


def _execute_payload(payload: Mapping[str, object]) -> tuple[BayesNetwork, str, Mapping[str, str], Mapping[str, float]]:
    if "variables" not in payload or "cpt" not in payload or "query" not in payload:
        raise ValueError("payload incomplete")
    network = BayesNetwork()
    for var_def in payload["variables"]:
        if not isinstance(var_def, Mapping):
            raise ValueError("variable definition must be an object")
        name = str(var_def.get("name", "")).strip()
        values = var_def.get("values") or ()
        parents = var_def.get("parents") or ()
        if not name or not values:
            raise ValueError("variable definition requires name and values")
        network.add_variable(name, values=tuple(values), parents=tuple(parents))
    cpt_def = payload.get("cpt") or {}
    if not isinstance(cpt_def, Mapping):
        raise ValueError("cpt must be a mapping")
    for variable, entries in cpt_def.items():
        if not isinstance(entries, list):
            raise ValueError("cpt entries must be a list")
        for entry in entries:
            if not isinstance(entry, Mapping):
                raise ValueError("cpt entry must be an object")
            condition = entry.get("given") or {}
            distribution = entry.get("distribution") or {}
            network.set_distribution(str(variable), given=condition, distribution=distribution)
    query = str(payload.get("query", "")).strip()
    if not query:
        raise ValueError("query is required")
    evidence = payload.get("evidence") or {}
    if not isinstance(evidence, Mapping):
        raise ValueError("evidence must be an object")
    posterior = network.posterior(query, evidence)
    return network, query, evidence, posterior


def _build_answer(query: str, posterior: Mapping[str, float]) -> tuple[Node, Node]:
    outcome_nodes = [
        liu_struct(
            tag=entity("bayes_outcome"),
            variable=entity(query),
            value=entity(value),
            probability=number(prob),
        )
        for value, prob in posterior.items()
    ]
    outcomes = list_node(outcome_nodes)
    description = ", ".join(f"{value}={prob:.3f}" for value, prob in posterior.items())
    answer_node = liu_struct(
        tag=entity("bayes_answer"),
        variable=entity(query),
        posterior=outcomes,
        answer=liu_text(f"P({query}|evidence) → {description}"),
    )
    posterior_node = liu_struct(
        tag=entity("bayes_posterior"),
        variable=entity(query),
        outcomes=outcomes,
    )
    return answer_node, posterior_node


def _network_context(network: BayesNetwork) -> Node:
    summary = network.summarize()
    variables = summary["variables"]
    variable_nodes = [
        liu_struct(
            tag=entity("bayes_variable"),
            name=entity(var["name"]),
            values=list_node(entity(value) for value in var["values"]),
            parents=list_node(entity(parent) for parent in var["parents"]),
        )
        for var in variables
    ]
    return liu_struct(
        tag=entity("bayes_network"),
        variable_count=number(summary["variable_count"]),
        edge_count=number(summary["edge_count"]),
        variables=list_node(variable_nodes),
    )


def _evidence_context(evidence: Mapping[str, str]) -> Node:
    if not evidence:
        return liu_struct(tag=entity("bayes_evidence"), entries=list_node(()))
    entries = [
        liu_struct(tag=entity("bayes_evidence_entry"), variable=entity(var), value=entity(val))
        for var, val in sorted(evidence.items())
    ]
    return liu_struct(tag=entity("bayes_evidence"), entries=list_node(entries))


__all__ = ["BayesHook", "maybe_route_bayes"]
