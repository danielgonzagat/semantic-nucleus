"""
Polynomial bridge – interpreta comandos POLY {json} para fatoração simbólica.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Tuple

from liu import Node, entity, list_node, number, struct as liu_struct, text as liu_text

from .polynomial_engine import PolynomialResult, factor_polynomial


@dataclass(frozen=True, slots=True)
class PolynomialHook:
    struct_node: Node
    answer_node: Node
    context_nodes: Tuple[Node, ...]
    quality: float
    trace_label: str


def maybe_route_polynomial(text: str) -> PolynomialHook | None:
    trimmed = (text or "").strip()
    if not trimmed:
        return None
    prefix, _, remainder = trimmed.partition(" ")
    if prefix.upper() != "POLY":
        return None
    payload_text = remainder.strip()
    if not payload_text:
        return None
    try:
        payload = json.loads(payload_text)
    except json.JSONDecodeError:
        return None
    try:
        result = factor_polynomial(payload)
    except ValueError:
        return None
    struct_node = liu_struct(
        tag=entity("poly_input"),
        variable=entity(result.variable),
        degree=number(result.degree),
    )
    answer_node = _build_answer(result)
    context_nodes = (
        _coefficients_context(result),
        _factor_context(result),
    )
    return PolynomialHook(
        struct_node=struct_node,
        answer_node=answer_node,
        context_nodes=context_nodes,
        quality=0.89,
        trace_label="MATH[POLY]",
    )


def _build_answer(result: PolynomialResult) -> Node:
    factors = " · ".join(f"({result.variable}-{root:.4f})" for _, root in result.factors) if result.factors else "irreducible"
    text_answer = f"{result.variable}^{result.degree} factored → {factors}"
    return liu_struct(
        tag=entity("poly_answer"),
        answer=liu_text(text_answer),
        residual=number(result.residual),
    )


def _coefficients_context(result: PolynomialResult) -> Node:
    entries = [
        liu_struct(tag=entity("poly_coeff"), degree=number(result.degree - index), value=number(value))
        for index, value in enumerate(result.coefficients)
    ]
    return liu_struct(
        tag=entity("poly_coefficients"),
        entries=list_node(entries),
    )


def _factor_context(result: PolynomialResult) -> Node:
    factor_nodes = [
        liu_struct(tag=entity("poly_factor"), coefficient=number(coeff), root=number(root))
        for coeff, root in result.factors
    ]
    return liu_struct(
        tag=entity("poly_factors"),
        residual=number(result.residual),
        factors=list_node(factor_nodes),
    )


__all__ = ["PolynomialHook", "maybe_route_polynomial"]
