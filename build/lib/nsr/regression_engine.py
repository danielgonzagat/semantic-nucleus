"""
Estatística clássica determinística: regressão linear múltipla via forma fechada.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Mapping, Sequence


@dataclass(frozen=True, slots=True)
class RegressionResult:
    features: tuple[str, ...]
    coefficients: tuple[tuple[str, float], ...]
    intercept: float | None
    r_squared: float
    mse: float
    sample_size: int
    residual_sum: float


def solve_linear_regression(payload: Mapping[str, object]) -> RegressionResult:
    """
    Resolve regressão linear múltipla determinística.

    payload esperado:
        {
            "features": ["x1", "x2"],
            "target": "y",                     # opcional (default: "target")
            "intercept": true,                 # opcional (default: true)
            "data": [
                {"x1": 1.0, "x2": 2.0, "y": 4.0},
                ...
            ]
        }
    """

    features = _parse_features(payload.get("features"))
    target_key = str(payload.get("target") or "target").strip() or "target"
    include_intercept = bool(payload.get("intercept", True))
    rows = payload.get("data") or []
    if not isinstance(rows, Sequence) or not rows:
        raise ValueError("data must be a non-empty list")
    matrix = []
    targets: list[float] = []
    for entry in rows:
        if not isinstance(entry, Mapping):
            raise ValueError("each data row must be an object")
        row_vector = [1.0] if include_intercept else []
        for feature in features:
            if feature not in entry:
                raise ValueError(f"feature '{feature}' missing from data row")
            row_vector.append(float(entry[feature]))
        if target_key not in entry:
            raise ValueError(f"target '{target_key}' missing from data row")
        matrix.append(row_vector)
        targets.append(float(entry[target_key]))
    beta = _least_squares(matrix, targets)
    predictions = _mat_vec_mul(matrix, beta)
    residuals = [y - y_hat for y, y_hat in zip(targets, predictions)]
    sample_size = len(targets)
    mse = sum(res * res for res in residuals) / sample_size
    residual_sum = sum(residuals)
    r_squared = _determine_r_squared(targets, predictions)
    intercept_value = beta[0] if include_intercept else None
    start_index = 1 if include_intercept else 0
    coeffs = tuple((features[i - start_index], beta[i]) for i in range(start_index, len(beta)))
    return RegressionResult(
        features=tuple(features),
        coefficients=coeffs,
        intercept=intercept_value,
        r_squared=round(r_squared, 6),
        mse=round(mse, 6),
        sample_size=sample_size,
        residual_sum=round(residual_sum, 6),
    )


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------


def _parse_features(raw: object) -> list[str]:
    if not isinstance(raw, Sequence) or not raw:
        raise ValueError("features must be a non-empty list")
    features = []
    for value in raw:
        label = str(value).strip()
        if not label:
            raise ValueError("feature names cannot be empty")
        features.append(label)
    return features


def _least_squares(matrix: Sequence[Sequence[float]], targets: Sequence[float]) -> List[float]:
    xt = _transpose(matrix)
    xtx = _matmul(xt, matrix)
    xty = _mat_vec_mul(xt, targets)
    xtx_inv = _invert_matrix(xtx)
    return _mat_vec_mul(xtx_inv, xty)


def _determine_r_squared(actual: Sequence[float], predicted: Sequence[float]) -> float:
    mean_value = sum(actual) / len(actual)
    ss_tot = sum((value - mean_value) ** 2 for value in actual)
    ss_res = sum((value - pred) ** 2 for value, pred in zip(actual, predicted))
    if ss_tot == 0:
        return 1.0 if ss_res == 0 else 0.0
    return 1.0 - (ss_res / ss_tot)


def _transpose(matrix: Sequence[Sequence[float]]) -> List[List[float]]:
    return [list(col) for col in zip(*matrix)]


def _matmul(a: Sequence[Sequence[float]], b: Sequence[Sequence[float]]) -> List[List[float]]:
    if len(a[0]) != len(b):
        raise ValueError("matrix dimensions mismatch")
    result = []
    b_transposed = _transpose(b)
    for row in a:
        result.append([sum(x * y for x, y in zip(row, col)) for col in b_transposed])
    return result


def _mat_vec_mul(matrix: Sequence[Sequence[float]], vector: Sequence[float]) -> List[float]:
    if len(matrix[0]) != len(vector):
        raise ValueError("matrix/vector dimensions mismatch")
    return [sum(value * weight for value, weight in zip(row, vector)) for row in matrix]


def _invert_matrix(matrix: Sequence[Sequence[float]]) -> List[List[float]]:
    size = len(matrix)
    if size != len(matrix[0]):
        raise ValueError("matrix must be square")
    augmented = [list(row) + [1.0 if i == j else 0.0 for j in range(size)] for i, row in enumerate(matrix)]
    for i in range(size):
        pivot = augmented[i][i]
        if abs(pivot) < 1e-12:
            raise ValueError("matrix is singular")
        factor = 1.0 / pivot
        augmented[i] = [value * factor for value in augmented[i]]
        for j in range(size):
            if j == i:
                continue
            ratio = augmented[j][i]
            augmented[j] = [curr - ratio * base for curr, base in zip(augmented[j], augmented[i])]
    return [row[size:] for row in augmented]


__all__ = ["RegressionResult", "solve_linear_regression"]
