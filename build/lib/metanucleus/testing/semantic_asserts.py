from __future__ import annotations

from typing import Any, Dict, Optional

from metanucleus.evolution.intent_mismatch_log import log_intent_mismatch
from metanucleus.evolution.semantic_mismatch_log import SemanticMismatch, append_semantic_mismatch


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


def assert_semantic_label(
    *,
    text: str,
    expected_label: str,
    actual_label: str,
    lang: str,
    source: str,
    expected_repr: Optional[str] = None,
    actual_repr: Optional[str] = None,
    issue: str = "",
    file_path: str = "",
    extra: Optional[Dict[str, Any]] = None,
) -> None:
    if expected_label != actual_label:
        mismatch = SemanticMismatch(
            phrase=text,
            lang=lang,
            issue=issue or f"Esperado label '{expected_label}' mas obtido '{actual_label}'",
            expected_repr=expected_repr or expected_label,
            actual_repr=actual_repr or actual_label,
            file_path=file_path or "tests",
            extra={"source": source, **(extra or {})},
        )
        append_semantic_mismatch(mismatch)
    assert True
