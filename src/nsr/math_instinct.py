"""
MathInstinct – camada determinística para avaliação de expressões matemáticas simples.
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from typing import Tuple
import math

from .ian import CHAR_TO_CODE, _normalize

RAW_EXPR_RE = re.compile(r"^[\s0-9A-Za-z+\-*/().]+$")
MATH_CHARS = set("0123456789+-*/()^%")
ALLOWED_BIN_OPS = (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow)
ALLOWED_UNARY_OPS = (ast.UAdd, ast.USub)
ALLOWED_CALLS = {"ABS": abs, "SQRT": math.sqrt}

LANGUAGE_KEYWORDS = {
    "pt": ("QUANTO É", "QUANTO E", "CALCULE", "CALCULA"),
    "en": ("WHAT IS", "CALCULATE", "COMPUTE"),
    "es": ("CUANTO ES", "CUAL ES", "CALCULA"),
    "fr": ("COMBIEN", "CALCULE"),
    "it": ("QUANTO È", "QUANTO E", "CALCOLA"),
}


@dataclass(frozen=True)
class MathUtterance:
    expression: str
    language: str
    role: str
    original: str


@dataclass(frozen=True)
class MathReply:
    text: str
    value: float
    language: str


class MathInstinct:
    def analyze(self, text: str) -> MathUtterance | None:
        expr_data = self._extract_expression(text)
        if expr_data is None:
            return None
        expression, language = expr_data
        return MathUtterance(
            expression=expression, language=language, role="MATH_EVAL", original=text
        )

    def evaluate(self, text: str) -> MathReply | None:
        utterance = self.analyze(text)
        if utterance is None:
            return None
        value = self._safe_eval(utterance.expression)
        formatted = self._format_value(value, utterance.language)
        return MathReply(text=formatted, value=value, language=utterance.language)

    @staticmethod
    def _format_value(value: float, language: str) -> str:
        if float(value).is_integer():
            return str(int(value))
        return f"{value:.6f}".rstrip("0").rstrip(".")

    @staticmethod
    def _extract_expression(text: str) -> Tuple[str, str] | None:
        stripped = text.strip()
        compact = stripped.replace(" ", "")
        if RAW_EXPR_RE.match(compact) and _looks_like_math(stripped):
            return stripped, "und"
        upper = _normalize_spaces(_shared_upper(stripped))
        for lang, keywords in LANGUAGE_KEYWORDS.items():
            for keyword in keywords:
                normalized_keyword = _normalize_keyword(keyword)
                idx = upper.find(normalized_keyword)
                if idx == -1:
                    continue
                expr = stripped[idx + len(keyword) :].strip(" ?!.,;:/")
                cleaned = _filter_expression(expr)
                if cleaned and _looks_like_math(cleaned):
                    return cleaned, lang
        return None

    def _safe_eval(self, expression: str) -> float:
        return evaluate_expression(expression)

    def _eval_node(self, node: ast.AST) -> float:
        return _eval_math_node(node)


def evaluate_expression(expression: str) -> float:
    expr_ast = ast.parse(expression, mode="eval")
    try:
        return float(_eval_math_node(expr_ast.body))
    except ZeroDivisionError as exc:
        raise ValueError("math expression contains invalid division") from exc


def _normalize_spaces(text: str) -> str:
    return re.sub(r"\s+", " ", text)


def _filter_expression(expr: str) -> str:
    allowed_chars = []
    for ch in expr:
        if ch.isdigit() or ch.isalpha() or ch in " +-*/().":
            allowed_chars.append(ch)
    return "".join(allowed_chars).strip()


def _normalize_keyword(keyword: str) -> str:
    try:
        return _shared_upper(keyword)
    except ValueError:
        return keyword.upper()


def _shared_upper(value: str) -> str:
    normalized = _normalize(value, CHAR_TO_CODE)
    return normalized


def _looks_like_math(text: str) -> bool:
    for ch in text:
        if ch.isdigit() or ch in MATH_CHARS:
            return True
    upper = _shared_upper(text)
    return any(func in upper for func in ALLOWED_CALLS.keys())


def _eval_math_node(node: ast.AST) -> float:
    if isinstance(node, ast.BinOp) and isinstance(node.op, ALLOWED_BIN_OPS):
        left = _eval_math_node(node.left)
        right = _eval_math_node(node.right)
        if isinstance(node.op, ast.Add):
            return left + right
        if isinstance(node.op, ast.Sub):
            return left - right
        if isinstance(node.op, ast.Mult):
            return left * right
        if isinstance(node.op, ast.Div):
            return left / right
        if isinstance(node.op, ast.Pow):
            return left**right
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ALLOWED_UNARY_OPS):
        operand = _eval_math_node(node.operand)
        return operand if isinstance(node.op, ast.UAdd) else -operand
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
        func_name = node.func.id.upper()
        if func_name in ALLOWED_CALLS and len(node.args) == 1:
            value = _eval_math_node(node.args[0])
            return float(ALLOWED_CALLS[func_name](value))
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return float(node.value)
    raise ValueError("Unsupported expression")


__all__ = ["MathInstinct", "MathUtterance", "MathReply", "evaluate_expression"]
