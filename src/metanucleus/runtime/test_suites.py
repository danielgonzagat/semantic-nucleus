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

MATH_FOCUS_SUITE = [
    TestCase(
        name="math_simple_add",
        input_text="1 + 2",
        expected=Expected(answer_contains="3"),
    ),
    TestCase(
        name="math_question_phrase",
        input_text="Quanto é 10 + 5?",
        expected=Expected(intent="question", answer_contains="15"),
    ),
]

TEST_SUITES = {
    "basic": BASIC_RUNTIME_SUITE,
    "math": MATH_FOCUS_SUITE,
}


def list_suites() -> list[str]:
    return sorted(TEST_SUITES.keys())


def get_suite(name: str):
    return TEST_SUITES.get(name)
