"""
Motor determinístico de fatoração polinomial univariada (coeficientes racionais).
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import Iterable, List, Sequence


@dataclass(frozen=True)
class PolynomialResult:
    variable: str
    degree: int
    coefficients: tuple[float, ...]
    factors: tuple[tuple[float, float], ...]  # representações (coeficiente, raiz)
    residual: float


def factor_polynomial(payload: dict) -> PolynomialResult:
    variable = str(payload.get("variable") or "x").strip() or "x"
    coeffs_raw = payload.get("coefficients")
    if not isinstance(coeffs_raw, Sequence) or not coeffs_raw:
        raise ValueError("coefficients must be a non-empty list")
    coeffs = [Fraction(value).limit_denominator(1_000_000) for value in coeffs_raw]
    while coeffs and coeffs[0] == 0:
        coeffs.pop(0)
    if not coeffs:
        raise ValueError("all coefficients are zero")
    degree = len(coeffs) - 1
    normalized = [float(value) for value in coeffs]
    roots = _rational_roots(coeffs)
    factors = []
    for root in roots:
        coeffs = _deflate(coeffs, root)
        factors.append((1.0, float(root)))
    residual = _residual(coeffs)
    return PolynomialResult(
        variable=variable,
        degree=degree,
        coefficients=tuple(normalized),
        factors=tuple(factors),
        residual=residual,
    )


def _rational_roots(coeffs: Sequence[Fraction]) -> List[Fraction]:
    leading = coeffs[0]
    constant = coeffs[-1]
    candidates = set()
    for p in _divisors(constant.numerator):
        for q in _divisors(leading.numerator):
            candidates.add(Fraction(p, q))
            candidates.add(Fraction(-p, q))
    roots = []
    for candidate in sorted(candidates):
        if candidate == 0 and coeffs[-1] != 0:
            continue
        value = _evaluate(coeffs, candidate)
        if value == 0:
            roots.append(candidate)
    return roots


def _divisors(value: int) -> Iterable[int]:
    value = abs(value)
    if value == 0:
        return [0]
    divisors = set()
    for i in range(1, value + 1):
        if value % i == 0:
            divisors.add(i)
    return divisors


def _evaluate(coeffs: Sequence[Fraction], x: Fraction) -> Fraction:
    result = Fraction(0)
    for coeff in coeffs:
        result = result * x + coeff
    return result


def _deflate(coeffs: Sequence[Fraction], root: Fraction) -> List[Fraction]:
    result = []
    accumulator = Fraction(0)
    for coeff in coeffs:
        accumulator = accumulator * root + coeff
        result.append(accumulator)
    remainder = result.pop()
    if remainder != 0:
        raise ValueError("root deflation produced non-zero remainder")
    return result


def _residual(coeffs: Sequence[Fraction]) -> float:
    if not coeffs:
        return 0.0
    if len(coeffs) == 1:
        value = float(coeffs[0])
        return 0.0 if abs(value - 1.0) < 1e-9 else abs(value)
    return float(sum(abs(float(coef)) for coef in coeffs))


__all__ = ["PolynomialResult", "factor_polynomial"]
