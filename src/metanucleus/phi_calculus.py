"""Φ-CALCULUS v1 – detects simple arithmetic expressions."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from .semantic_mapper import SemanticParse, SemanticToken


@dataclass
class CalculusResult:
    kind: str  # "none" | "arithmetic"
    result: Optional[float]
    expression_normalized: Optional[str]
    steps: List[str] = field(default_factory=list)
    confidence: float = 0.0


_NUM_WORDS_PT = {
    "zero": 0,
    "um": 1,
    "uma": 1,
    "dois": 2,
    "duas": 2,
    "tres": 3,
    "três": 3,
    "quatro": 4,
    "cinco": 5,
    "seis": 6,
    "sete": 7,
    "oito": 8,
    "nove": 9,
    "dez": 10,
}

_OP_TOKENS = {
    "+": "+",
    "mais": "+",
    "-": "-",
    "menos": "-",
    "*": "*",
    "x": "*",
    "vezes": "*",
    "/": "/",
    "dividido": "/",
    "dividido_por": "/",
}


def _tok_to_number(token: SemanticToken) -> Optional[float]:
    if token.is_number:
        try:
            return float(token.lower.replace(",", "."))
        except ValueError:
            return None
    if token.lower in _NUM_WORDS_PT:
        return float(_NUM_WORDS_PT[token.lower])
    return None


def _tok_to_operator(token: SemanticToken) -> Optional[str]:
    if token.lower == "dividido":
        return "/"
    return _OP_TOKENS.get(token.lower)


def phi_calculus(parse: SemanticParse) -> CalculusResult:
    numbers: List[float] = []
    operators: List[str] = []
    steps: List[str] = []

    for token in parse.tokens:
        num = _tok_to_number(token)
        if num is not None:
            numbers.append(num)
            steps.append(f"detectado número: {token.text} -> {num}")
            continue
        op = _tok_to_operator(token)
        if op is not None:
            operators.append(op)
            steps.append(f"detectado operador: {token.text} -> {op}")

    if len(numbers) < 2 or not operators:
        return CalculusResult(kind="none", result=None, expression_normalized=None, steps=steps, confidence=0.0)

    value = numbers[0]
    expr_parts = [str(numbers[0])]
    op_idx = 0
    num_idx = 1

    while op_idx < len(operators) and num_idx < len(numbers):
        op = operators[op_idx]
        num = numbers[num_idx]
        expr_parts.append(op)
        expr_parts.append(str(num))
        if op == "+":
            value += num
        elif op == "-":
            value -= num
        elif op == "*":
            value *= num
        elif op == "/":
            if num == 0:
                steps.append("divisão por zero detectada; abortando cálculo")
                return CalculusResult(
                    kind="arithmetic",
                    result=None,
                    expression_normalized=" ".join(expr_parts),
                    steps=steps,
                    confidence=0.1,
                )
            value /= num
        steps.append(f"aplicando: {op} {num} -> valor atual = {value}")
        op_idx += 1
        num_idx += 1

    expr_norm = " ".join(expr_parts)
    steps.append(f"expressão normalizada: {expr_norm}")
    steps.append(f"resultado final: {value}")
    confidence = 0.6 + min(0.3, 0.05 * (len(numbers) + len(operators)))
    return CalculusResult(kind="arithmetic", result=value, expression_normalized=expr_norm, steps=steps, confidence=confidence)
