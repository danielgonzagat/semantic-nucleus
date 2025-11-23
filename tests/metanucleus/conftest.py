from __future__ import annotations

import pytest

from metanucleus.semantics.intent_lexicon import infer_intent, detect_language, load_intent_lexicon


class KernelIntentDetector:
    def __init__(self) -> None:
        self.lexicon = load_intent_lexicon()

    def detect_intent(self, text: str) -> str:
        _, intent = infer_intent(text, self.lexicon)
        return intent or "unknown"

    def detect_lang(self, text: str) -> str:
        return detect_language(text, self.lexicon)


@pytest.fixture()
def kernel() -> KernelIntentDetector:
    return KernelIntentDetector()
