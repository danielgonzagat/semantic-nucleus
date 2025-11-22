"""
Utilidades para carregar suites de teste personalizados.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import List

from metanucleus.test.testcore import Expected, TestCase


class SuiteFormatError(ValueError):
    """Erro levantado quando o arquivo de suite está malformado."""


def load_suite_file(path: Path) -> List[TestCase]:
    """
    Lê um arquivo JSON no formato:

    {
        "tests": [
            {
                "name": "saudacao",
                "input": "Oi",
                "expected": {
                    "intent": "greeting",
                    "lang": "pt",
                    "answer_contains": "Metanúcleo"
                }
            }
        ]
    }
    """

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SuiteFormatError(f"JSON inválido em {path}") from exc

    tests_data = payload.get("tests")
    if not isinstance(tests_data, list) or not tests_data:
        raise SuiteFormatError("Campo 'tests' deve ser uma lista não vazia.")

    cases: List[TestCase] = []
    for entry in tests_data:
        if not isinstance(entry, dict):
            raise SuiteFormatError("Cada teste deve ser um objeto.")
        name = entry.get("name")
        input_text = entry.get("input")
        expected_data = entry.get("expected", {})
        if not name or not input_text:
            raise SuiteFormatError("Cada teste precisa de 'name' e 'input'.")
        if not isinstance(expected_data, dict):
            raise SuiteFormatError("'expected' deve ser um objeto.")
        expected = Expected(
            intent=expected_data.get("intent"),
            lang=expected_data.get("lang"),
            answer_prefix=expected_data.get("answer_prefix"),
            answer_contains=expected_data.get("answer_contains"),
        )
        cases.append(TestCase(name=name, input_text=input_text, expected=expected))

    return cases


__all__ = ["load_suite_file", "SuiteFormatError"]
