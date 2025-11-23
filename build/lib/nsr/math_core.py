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
WORD_SPLIT_PATTERN = re.compile(r"[^A-Z0-9]+")
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
    "power": {
        "pt": ("POTENCIA", "POTENCIA DE", "ELEVADO A", "ELEVADO"),
        "en": ("POWER", "RAISED TO", "TO THE POWER"),
        "es": ("POTENCIA", "ELEVADO A"),
        "fr": ("PUISSANCE", "ELEVE A", "ELEVE"),
        "it": ("POTENZA", "ELEVATO A"),
    },
    "percent": {
        "pt": ("PORCENTO", "POR CENTO", "PORCENTAGEM", "PERCENTUAL"),
        "en": ("PERCENT", "PERCENTAGE"),
        "es": ("POR CIENTO", "PORCENTAJE"),
        "fr": ("POURCENT", "POURCENTAGE"),
        "it": ("PERCENTO", "PERCENTUALE"),
    },
}

LANGUAGE_KEYWORD_CACHE: Dict[str, Tuple[str, ...]] = {}
NUMBER_WORDS: Dict[str, Dict[str, float]] = {
    "pt": {
        "ZERO": 0,
        "UM": 1,
        "UMA": 1,
        "DOIS": 2,
        "DUAS": 2,
        "TRES": 3,
        "TRES": 3,
        "QUATRO": 4,
        "CINCO": 5,
        "SEIS": 6,
        "SETE": 7,
        "OITO": 8,
        "NOVE": 9,
        "DEZ": 10,
        "ONZE": 11,
        "DOZE": 12,
        "TREZE": 13,
        "QUATORZE": 14,
        "QUINZE": 15,
        "DEZESSEIS": 16,
        "DEZESSETE": 17,
        "DEZOITO": 18,
        "DEZENOVE": 19,
        "VINTE": 20,
        "TRINTA": 30,
        "QUARENTA": 40,
        "CINQUENTA": 50,
        "SESSENTA": 60,
        "SETENTA": 70,
        "OITENTA": 80,
        "NOVENTA": 90,
        "CEM": 100,
    },
    "en": {
        "ZERO": 0,
        "ONE": 1,
        "TWO": 2,
        "THREE": 3,
        "FOUR": 4,
        "FIVE": 5,
        "SIX": 6,
        "SEVEN": 7,
        "EIGHT": 8,
        "NINE": 9,
        "TEN": 10,
        "ELEVEN": 11,
        "TWELVE": 12,
        "THIRTEEN": 13,
        "FOURTEEN": 14,
        "FIFTEEN": 15,
        "SIXTEEN": 16,
        "SEVENTEEN": 17,
        "EIGHTEEN": 18,
        "NINETEEN": 19,
        "TWENTY": 20,
        "THIRTY": 30,
        "FORTY": 40,
        "FIFTY": 50,
        "SIXTY": 60,
        "SEVENTY": 70,
        "EIGHTY": 80,
        "NINETY": 90,
        "HUNDRED": 100,
    },
    "es": {
        "CERO": 0,
        "UNO": 1,
        "UNA": 1,
        "DOS": 2,
        "TRES": 3,
        "CUATRO": 4,
        "CINCO": 5,
        "SEIS": 6,
        "SIETE": 7,
        "OCHO": 8,
        "NUEVE": 9,
        "DIEZ": 10,
        "ONCE": 11,
        "DOCE": 12,
        "TRECE": 13,
        "CATORCE": 14,
        "QUINCE": 15,
        "DIECISEIS": 16,
        "DIECISIETE": 17,
        "DIECIOCHO": 18,
        "DIECINUEVE": 19,
        "VEINTE": 20,
        "TREINTA": 30,
        "CUARENTA": 40,
        "CINCUENTA": 50,
        "SESENTA": 60,
        "SETENTA": 70,
        "OCHENTA": 80,
        "NOVENTA": 90,
        "CIEN": 100,
    },
    "fr": {
        "ZERO": 0,
        "UN": 1,
        "UNE": 1,
        "DEUX": 2,
        "TROIS": 3,
        "QUATRE": 4,
        "CINQ": 5,
        "SIX": 6,
        "SEPT": 7,
        "HUIT": 8,
        "NEUF": 9,
        "DIX": 10,
        "ONZE": 11,
        "DOUZE": 12,
        "TREIZE": 13,
        "QUATORZE": 14,
        "QUINZE": 15,
        "SEIZE": 16,
        "DIXSEPT": 17,
        "DIXHUIT": 18,
        "DIXNEUF": 19,
        "VINGT": 20,
        "TRENTE": 30,
        "QUARANTE": 40,
        "CINQUANTE": 50,
        "SOIXANTE": 60,
        "SOIXANTEDIX": 70,
        "QUATREVINGT": 80,
        "QUATREVINGTDIX": 90,
        "CENT": 100,
    },
    "it": {
        "ZERO": 0,
        "UNO": 1,
        "UNA": 1,
        "DUE": 2,
        "TRE": 3,
        "QUATTRO": 4,
        "CINQUE": 5,
        "SEI": 6,
        "SETTE": 7,
        "OTTO": 8,
        "NOVE": 9,
        "DIECI": 10,
        "UNDICI": 11,
        "DODICI": 12,
        "TREDICI": 13,
        "QUATTORDICI": 14,
        "QUINDICI": 15,
        "SEDICI": 16,
        "DICIASSETTE": 17,
        "DICIOTTO": 18,
        "DICIANOVE": 19,
        "VENTI": 20,
        "TRENTA": 30,
        "QUARANTA": 40,
        "CINQUANTA": 50,
        "SESSANTA": 60,
        "SETTANTA": 70,
        "OTTANTA": 80,
        "NOVANTA": 90,
        "CENTO": 100,
    },
}


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
    numbers = _extract_numbers(text, normalized, language)
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


def _extract_numbers(text: str, normalized: str, language: str | None) -> Tuple[float, ...]:
    values = []
    values.extend(_extract_numeric_literals(text))
    values.extend(_extract_number_words(normalized, language))
    return tuple(values)


def _extract_numeric_literals(text: str) -> Tuple[float, ...]:
    values = []
    for match in NUMBER_PATTERN.finditer(text):
        token = match.group(0).replace(",", ".")
        try:
            values.append(float(token))
        except ValueError:
            continue
    return tuple(values)


def _extract_number_words(normalized: str, language: str | None) -> Tuple[float, ...]:
    if not normalized:
        return ()
    tokens = [token for token in WORD_SPLIT_PATTERN.split(normalized) if token]
    if language and language != "und":
        languages: Iterable[str] = (language,)
    else:
        languages = LANGUAGE_ORDER
    results: list[float] = []
    for token in tokens:
        for lang in languages:
            mapping = NUMBER_WORDS.get(lang)
            if mapping is None:
                continue
            value = mapping.get(token)
            if value is not None:
                results.append(float(value))
                break
    return tuple(results)


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


def _build_power(values: Sequence[float]) -> str | None:
    operands = _require_operands(2, values)
    if operands is None:
        return None
    base, exponent = operands[:2]
    return f"{_format_number(base)}**{_format_number(exponent)}"


def _build_percent(values: Sequence[float]) -> str | None:
    operands = _require_operands(2, values)
    if operands is None:
        return None
    percentage, total = operands[:2]
    return f"({_format_number(percentage)}*{_format_number(total)})/100"


EXPRESSION_BUILDERS = {
    "sqrt": _build_sqrt,
    "sum": _build_sum,
    "difference": _build_difference,
    "product": _build_product,
    "quotient": _build_quotient,
    "power": _build_power,
    "percent": _build_percent,
}


__all__ = ["MathInstruction", "MathCoreResult", "parse_math_phrase", "evaluate_math_phrase"]
