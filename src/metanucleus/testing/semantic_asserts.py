from __future__ import annotations

from typing import Any

from metanucleus.evolution.intent_mismatch_log import log_intent_mismatch


def assert_intent(kernel: Any, text: str, expected_intent: str) -> None:
    actual = kernel.detect_intent(text)
    if actual != expected_intent:
        lang = None
        if hasattr(kernel, "detect_lang"):
            try:
                lang = kernel.detect_lang(text)
            except Exception:  # pragma: no cover
                lang = None
        log_intent_mismatch(
            text=text,
            expected_intent=expected_intent,
            actual_intent=actual or "unknown",
            lang=lang,
            source="test",
        )
        raise AssertionError(
            f"INTENT_MISMATCH: esperado '{expected_intent}' mas obtido '{actual}' para {text!r}"
        )
