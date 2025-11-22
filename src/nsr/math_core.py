"""
Math-Core – parser determinístico de frases matemáticas → meta-instruções → cálculo auditável.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Dict, Iterable, Sequence, Tuple

from .math_instinct import evaluate_expression

NUMBER_PATTERN = re.compile(r"[-+]?\d+(?:[.,]\d+)?")
LANGUAGE_ORDER = ("pt", "en", "es", "fr", "it")

OPERATION_KEYWORDS: Dict[str, Dict[str, Tuple[str, ...]]] = {
    "sqrt": {
        "pt": ("RAIZ QUADRADA", "RAIZ DE", "RAIZ"),
        "en": ("SQUARE ROOT", "ROOT OF", "ROOT"),
        "es": ("RAIZ CUADRADA", "RAIZ DE"),
        "fr": ("RACINE CARREE", "RACINE DE"),
        "it": ("RADICE QUADRATA", "RADICE DI"),
    },
    "sum": {
        "pt": ("SOMA", "SOMAR", "SOME", "MAIS"),
        "en": ("SUM", "ADD", "PLUS"),
        "es": ("SUMA", "SUMAR", "MAS"),
        "fr": ("SOMME", "PLUS", "AJOUTE"),
        "it": ("SOMMA", "PIU", "AGGIUNGI"),
    },
    "difference": {
        "pt": ("DIFERENCA", "MENOS", "SUBTRAIA"),
        "en": ("DIFFERENCE", "MINUS", "SUBTRACT"),
        "es": ("DIFERENCIA", "MENOS", "RESTA"),
        "fr": ("DIFFERENCE", "MOINS", "SOUSTRAIT"),
        "it": ("DIFFERENZA", "MENO", "SOTTRAI"),
    },
    "product": {
        "pt": ("PRODUTO", "VEZES", "MULTIPLIQUE"),
        "en": ("PRODUCT", "TIMES", "MULTIPLY"),
        "es": ("PRODUCTO", "POR", "MULTIPLICA"),
        "fr": ("PRODUIT", "FOIS", "MULTIPLIE"),
        "it": ("PRODOTTO", "PER", "MOLTIPLICA"),
    },
    "quotient": {
        "pt": ("DIVISAO", "DIVIDIDO", "DIVIDA"),
        "en": ("QUOTIENT", "DIVIDED", "DIVIDE"),
        "es": ("DIVISION", "DIVIDIDO", "DIVIDE"),
        "fr": ("DIVISION", "DIVISE", "DIVISEE"),
        "it": ("DIVISIONE", "DIVISO", "DIVIDI"),
    },
}

LANGUAGE_KEYWORD_CACHE: Dict[str, Tuple[str, ...]] = {}


@dataclass(frozen=True)
class MathInstruction:
    operation: str
    operands: Tuple[float, ...]
    language: str
    expression: str
    original: str

    def as_term(self):
        from .lc_omega import LCTerm

        children = tuple(LCTerm(kind="NUM", label=_format_number(value)) for value in self.operands)
        return LCTerm(kind="MATH_OP", label=self.operation.upper(), children=children)


@dataclass(frozen=True)
class MathCoreResult:
    instruction: MathInstruction
    value: float

    def as_term(self):
        return self.instruction.as_term()


def parse_math_phrase(text: str) -> MathInstruction | None:
    normalized = _normalize_upper(text)
    language = _detect_language(normalized)
    operation = _detect_operation(normalized, language) or _detect_operation(normalized, None)
    numbers = _extract_numbers(text)
    if operation is None and numbers:
        # fallback to raw arithmetic when input already resembles expression
        expression = _strip_trailing_punctuation(text).strip()
        if _looks_like_expression(expression):
            return MathInstruction(
                operation="expression",
                operands=tuple(numbers),
                language=language or "und",
                expression=expression,
                original=text,
            )
        return None
    if operation is None:
        return None
    builder = EXPRESSION_BUILDERS.get(operation)
    if builder is None:
        return None
    expression = builder(numbers)
    if expression is None:
        return None
    return MathInstruction(
        operation=operation,
        operands=tuple(numbers),
        language=language or "und",
        expression=expression,
        original=text,
    )


def evaluate_math_phrase(text: str) -> MathCoreResult | None:
    instruction = parse_math_phrase(text)
    if instruction is None:
        return None
    value = evaluate_expression(instruction.expression)
    return MathCoreResult(instruction=instruction, value=value)


def _extract_numbers(text: str) -> Tuple[float, ...]:
    values = []
    for match in NUMBER_PATTERN.finditer(text):
        token = match.group(0).replace(",", ".")
        try:
            values.append(float(token))
        except ValueError:
            continue
    return tuple(values)


def _detect_language(normalized: str) -> str:
    for language in LANGUAGE_ORDER:
        keywords = LANGUAGE_KEYWORD_CACHE.setdefault(language, _language_keywords(language))
        if any(keyword in normalized for keyword in keywords):
            return language
    return "und"


def _detect_operation(normalized: str, language: str | None) -> str | None:
    languages: Iterable[str]
    if language:
        languages = (language,)
    else:
        languages = LANGUAGE_ORDER
    for lang in languages:
        for operation, mapping in OPERATION_KEYWORDS.items():
            for keyword in mapping.get(lang, ()):
                if keyword in normalized:
                    return operation
    return None


def _language_keywords(language: str) -> Tuple[str, ...]:
    keywords = []
    for mapping in OPERATION_KEYWORDS.values():
        keywords.extend(mapping.get(language, ()))
    keywords.sort(key=len, reverse=True)
    return tuple(dict.fromkeys(keywords))  # preserve order, drop duplicates


def _normalize_upper(text: str) -> str:
    decomposed = unicodedata.normalize("NFD", text)
    stripped = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return stripped.upper()


def _strip_trailing_punctuation(text: str) -> str:
    return text.rstrip(" ?!.,;")


def _looks_like_expression(text: str) -> bool:
    return bool(re.search(r"[+\-*/^]", text))


def _require_operands(count: int, values: Sequence[float]) -> Tuple[float, ...] | None:
    if len(values) < count:
        return None
    return tuple(values)


def _format_number(value: float) -> str:
    if float(value).is_integer():
        return str(int(value))
    return f"{value:.15g}"


def _build_sqrt(values: Sequence[float]) -> str | None:
    operands = _require_operands(1, values)
    if operands is None:
        return None
    return f"SQRT({_format_number(operands[0])})"


def _build_sum(values: Sequence[float]) -> str | None:
    if len(values) < 2:
        return None
    return "+".join(_format_number(value) for value in values)


def _build_difference(values: Sequence[float]) -> str | None:
    operands = _require_operands(2, values)
    if operands is None:
        return None
    head, tail = operands[0], operands[1]
    return f"{_format_number(head)}-{_format_number(tail)}"


def _build_product(values: Sequence[float]) -> str | None:
    if len(values) < 2:
        return None
    return "*".join(_format_number(value) for value in values)


def _build_quotient(values: Sequence[float]) -> str | None:
    operands = _require_operands(2, values)
    if operands is None:
        return None
    numerator, denominator = operands
    return f"{_format_number(numerator)}/{_format_number(denominator)}"


EXPRESSION_BUILDERS = {
    "sqrt": _build_sqrt,
    "sum": _build_sum,
    "difference": _build_difference,
    "product": _build_product,
    "quotient": _build_quotient,
}


__all__ = ["MathInstruction", "MathCoreResult", "parse_math_phrase", "evaluate_math_phrase"]
