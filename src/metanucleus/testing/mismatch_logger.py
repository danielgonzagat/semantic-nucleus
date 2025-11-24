"""
Logger centralizado de mismatches para autoevolução.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Literal, Optional

from metanucleus.utils.project import get_project_root
from metanucleus.utils.log_rotation import enforce_log_limit

_ROOT = get_project_root(Path(__file__))
_LOG_DIR = _ROOT / ".metanucleus"
_LOG_FILE = _LOG_DIR / "mismatch_log.jsonl"
_MAX_LOG_LINES_DEFAULT = 5000
_MAX_LOG_LINES = _MAX_LOG_LINES_DEFAULT

MismatchType = Literal[
    "intent_mismatch",
    "semantic_cost_mismatch",
    "frame_mismatch",
    "calc_rule_mismatch",
]


def _ensure_log_dir() -> None:
    _LOG_DIR.mkdir(parents=True, exist_ok=True)


def _append_record(record: Dict[str, Any]) -> None:
    _ensure_log_dir()
    with _LOG_FILE.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")
    enforce_log_limit(_LOG_FILE, _MAX_LOG_LINES)


@dataclass
class IntentMismatch:
    type: str
    input: str
    language: str
    expected_intent: str
    predicted_intent: str

    def log(self) -> None:
        _append_record(asdict(self))


@dataclass
class FrameMismatch:
    type: str
    input: str
    language: str
    predicate: str
    expected_roles: Dict[str, str]
    predicted_roles: Dict[str, str]
    note: Optional[str] = None

    def log(self) -> None:
        _append_record(asdict(self))


@dataclass
class CalcRuleMismatch:
    type: str
    rule_id: str
    input: str
    expected: str
    predicted: str

    def log(self) -> None:
        _append_record(asdict(self))


def log_intent_mismatch(
    *,
    input_text: str,
    language: str,
    expected: str,
    predicted: str,
) -> None:
    IntentMismatch(
        type="intent_mismatch",
        input=input_text,
        language=language,
        expected_intent=expected,
        predicted_intent=predicted,
    ).log()


def log_frame_mismatch(
    *,
    input_text: str,
    language: str,
    predicate: str,
    expected_roles: Dict[str, str],
    predicted_roles: Dict[str, str],
    note: Optional[str] = None,
) -> None:
    FrameMismatch(
        type="frame_mismatch",
        input=input_text,
        language=language,
        predicate=predicate,
        expected_roles=expected_roles,
        predicted_roles=predicted_roles,
        note=note,
    ).log()


def log_calc_rule_mismatch(
    *,
    rule_id: str,
    input_expr: str,
    expected: str,
    predicted: str,
) -> None:
    CalcRuleMismatch(
        type="calc_rule_mismatch",
        rule_id=rule_id,
        input=input_expr,
        expected=expected,
        predicted=predicted,
    ).log()


__all__ = [
    "log_intent_mismatch",
    "log_frame_mismatch",
    "log_calc_rule_mismatch",
    "MismatchType",
    "configure_mismatch_log_limit",
]


def configure_mismatch_log_limit(limit: int | None) -> None:
    global _MAX_LOG_LINES
    if limit is None or limit <= 0:
        _MAX_LOG_LINES = _MAX_LOG_LINES_DEFAULT
    else:
        _MAX_LOG_LINES = limit
