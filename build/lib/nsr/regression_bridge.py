"""
Regression bridge – interpreta comandos REGRESS {json} e executa regressão linear.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Tuple

from liu import Node, entity, list_node, number, struct as liu_struct, text as liu_text

from .regression_engine import RegressionResult, solve_linear_regression


@dataclass(frozen=True, slots=True)
class RegressionHook:
    struct_node: Node
    answer_node: Node
    context_nodes: Tuple[Node, ...]
    quality: float
    trace_label: str


def maybe_route_regression(text: str) -> RegressionHook | None:
    trimmed = (text or "").strip()
    if not trimmed:
        return None
    prefix, _, remainder = trimmed.partition(" ")
    if prefix.upper() != "REGRESS":
        return None
    payload_text = remainder.strip()
    if not payload_text:
        return None
    try:
        payload = json.loads(payload_text)
    except json.JSONDecodeError:
        return None
    try:
        result = solve_linear_regression(payload)
    except ValueError:
        return None
    struct_node = liu_struct(
        tag=entity("regress_input"),
        feature_count=number(len(result.features)),
        sample_size=number(result.sample_size),
    )
    answer_node = _build_answer(result)
    context_nodes = (
        _coefficients_context(result),
        _metrics_context(result),
    )
    return RegressionHook(
        struct_node=struct_node,
        answer_node=answer_node,
        context_nodes=context_nodes,
        quality=0.9,
        trace_label="STAT[REGRESSION]",
    )


def _build_answer(result: RegressionResult) -> Node:
    coeff_text = ", ".join(f"{name}={value:.4f}" for name, value in result.coefficients)
    intercept_text = (
        f"intercept={result.intercept:.4f}, " if result.intercept is not None else ""
    )
    answer = liu_text(f"β: {intercept_text}{coeff_text}")
    return liu_struct(
        tag=entity("regress_answer"),
        answer=answer,
        r_squared=number(result.r_squared),
        mse=number(result.mse),
    )


def _coefficients_context(result: RegressionResult) -> Node:
    entries = [
        liu_struct(
            tag=entity("regress_coeff"),
            feature=entity(feature),
            value=number(value),
        )
        for feature, value in result.coefficients
    ]
    return liu_struct(
        tag=entity("regress_coefficients"),
        intercept=number(result.intercept or 0.0),
        coefficients=list_node(entries),
    )


def _metrics_context(result: RegressionResult) -> Node:
    return liu_struct(
        tag=entity("regress_metrics"),
        sample_size=number(result.sample_size),
        residual_sum=number(result.residual_sum),
        r_squared=number(result.r_squared),
        mse=number(result.mse),
    )


__all__ = ["RegressionHook", "maybe_route_regression"]
