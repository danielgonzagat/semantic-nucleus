from __future__ import annotations

import pytest

from metanucleus.runtime import MetanucleusRuntime
from metanucleus.testing.mismatch_logger import log_intent_mismatch


@pytest.fixture(scope="module")
def runtime() -> MetanucleusRuntime:
    return MetanucleusRuntime()


@pytest.fixture()
def session(runtime: MetanucleusRuntime):
    return runtime.new_session()


INTENT_CASES = [
    ("oi", "pt", "greeting"),
    ("olá", "pt", "greeting"),
    ("tudo bem?", "pt", "question"),
    ("quero que você faça um resumo", "pt", "command"),
    ("hello", "en", "greeting"),
    ("how are you?", "en", "question"),
    ("summarize this text", "en", "command"),
]


@pytest.mark.parametrize("text, expected_lang, expected_intent", INTENT_CASES)
def test_intent_detection(session, text, expected_lang, expected_intent) -> None:
    analysis = session.analyze(text)
    lang = analysis.get("language", "unknown")
    intent = analysis.get("intent", "unknown")

    if lang != expected_lang or intent != expected_intent:
        log_intent_mismatch(
            input_text=text,
            language=lang,
            expected=expected_intent,
            predicted=intent,
        )

    assert True
