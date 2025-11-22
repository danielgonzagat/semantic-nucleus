"""
Test suites pré-definidas para o comando /testcore.
"""

from __future__ import annotations

from metanucleus.test.testcore import TestCase, Expected


BASIC_RUNTIME_SUITE = [
    TestCase(
        name="greeting_pt",
        input_text="Oi Metanúcleo!",
        expected=Expected(intent="greeting", lang="pt", answer_contains="Metanúcleo"),
    ),
    TestCase(
        name="math_question",
        input_text="Quanto é 2 + 3?",
        expected=Expected(intent="question", lang="pt", answer_contains="5"),
    ),
    TestCase(
        name="english_command",
        input_text="Explain 4 * 7 to me",
        expected=Expected(lang="en"),
    ),
]
