from __future__ import annotations

from metanucleus.testing.semantic_asserts import assert_intent


def test_pt_question(kernel):
    assert_intent(kernel, "Por que o carro corre?", "question")


def test_pt_greeting(kernel):
    assert_intent(kernel, "Bom dia, tudo bem?", "greeting")


def test_en_question(kernel):
    assert_intent(kernel, "How are you doing today?", "question")


def test_en_greeting(kernel):
    assert_intent(kernel, "Hello there!", "greeting")


def test_es_question(kernel):
    assert_intent(kernel, "¿Dónde está la biblioteca?", "question")


def test_fr_greeting(kernel):
    assert_intent(kernel, "Bonjour, tout va bien?", "greeting")


def test_it_greeting(kernel):
    assert_intent(kernel, "Ciao, buon pomeriggio", "greeting")


def test_de_greeting(kernel):
    assert_intent(kernel, "Guten Morgen, alles certo?", "greeting")
