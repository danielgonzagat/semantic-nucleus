"""
MathInstinct – camada determinística para avaliação de expressões matemáticas simples.
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from typing import Tuple

RAW_EXPR_RE = re.compile(r"^[\s0-9+\-*/().]+$")
ALLOWED_BIN_OPS = (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow)
ALLOWED_UNARY_OPS = (ast.UAdd, ast.USub)

LANGUAGE_KEYWORDS = {
    "pt": ("QUANTO É", "CALCULE", "CALCULA"),
    "en": ("WHAT IS", "CALCULATE", "COMPUTE"),
    "es": ("CUANTO ES", "CALCULA"),
    "fr": ("COMBIEN", "CALCULE"),
    "it": ("QUANTO E", "CALCOLA"),
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
        return MathUtterance(expression=expression, language=language, role="MATH_EVAL", original=text)

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
        if RAW_EXPR_RE.match(compact):
            return stripped, "und"
        upper = _normalize_spaces(stripped.upper())
        for lang, keywords in LANGUAGE_KEYWORDS.items():
            for keyword in keywords:
                idx = upper.find(keyword)
                if idx == -1:
                    continue
                expr = stripped[idx + len(keyword) :].strip(" ?!.,;:/")
                cleaned = _filter_expression(expr)
                if cleaned:
                    return cleaned, lang
        return None

    def _safe_eval(self, expression: str) -> float:
        expr_ast = ast.parse(expression, mode="eval")
        return float(self._eval_node(expr_ast.body))

    def _eval_node(self, node: ast.AST) -> float:
        if isinstance(node, ast.BinOp) and isinstance(node.op, ALLOWED_BIN_OPS):
            left = self._eval_node(node.left)
            right = self._eval_node(node.right)
            if isinstance(node.op, ast.Add):
                return left + right
            if isinstance(node.op, ast.Sub):
                return left - right
            if isinstance(node.op, ast.Mult):
                return left * right
            if isinstance(node.op, ast.Div):
                return left / right
            if isinstance(node.op, ast.Pow):
                return left ** right
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ALLOWED_UNARY_OPS):
            operand = self._eval_node(node.operand)
            return operand if isinstance(node.op, ast.UAdd) else -operand
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return float(node.value)
        raise ValueError("Unsupported expression")


def _normalize_spaces(text: str) -> str:
    return re.sub(r"\s+", " ", text)


def _filter_expression(expr: str) -> str:
    allowed_chars = []
    for ch in expr:
        if ch.isdigit() or ch in " +-*/().":
            allowed_chars.append(ch)
    return "".join(allowed_chars).strip()


__all__ = ["MathInstinct", "MathUtterance", "MathReply"]
