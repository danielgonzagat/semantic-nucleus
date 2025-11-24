"""
Registro determinístico de mismatches de intent para autoevolução.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from metanucleus.utils.project import get_project_root
from metanucleus.utils.log_rotation import enforce_log_limit

_PROJECT_ROOT = get_project_root(Path(__file__))
_META_DIR = _PROJECT_ROOT / ".meta"
_META_DIR.mkdir(parents=True, exist_ok=True)
INTENT_MISMATCH_LOG_PATH = _META_DIR / "intent_mismatches.jsonl"
MAX_INTENT_LOG_LINES_DEFAULT = 5000
_MAX_INTENT_LOG_LINES = MAX_INTENT_LOG_LINES_DEFAULT


@dataclass(slots=True)
class IntentMismatchLogEntry:
    text: str
    expected_intent: str
    actual_intent: str
    lang: Optional[str]
    source: str
    timestamp: str
    extra: Dict[str, Any]


def log_intent_mismatch(
    *,
    text: str,
    expected_intent: str,
    actual_intent: str,
    lang: Optional[str],
    source: str,
    extra: Optional[Dict[str, Any]] = None,
    path: Path = INTENT_MISMATCH_LOG_PATH,
) -> None:
    entry = IntentMismatchLogEntry(
        text=text,
        expected_intent=expected_intent,
        actual_intent=actual_intent,
        lang=lang,
        source=source,
        timestamp=datetime.now(timezone.utc).isoformat(),
        extra=extra or {},
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(asdict(entry), ensure_ascii=False) + "\n")
    enforce_log_limit(path, _MAX_INTENT_LOG_LINES)


def configure_intent_log_limit(limit: int | None) -> None:
    global _MAX_INTENT_LOG_LINES
    if limit is None or limit <= 0:
        _MAX_INTENT_LOG_LINES = MAX_INTENT_LOG_LINES_DEFAULT
    else:
        _MAX_INTENT_LOG_LINES = limit


def load_intent_mismatch_logs(
    *,
    limit: Optional[int] = None,
    path: Path = INTENT_MISMATCH_LOG_PATH,
    since: Optional[datetime] = None,
) -> List[IntentMismatchLogEntry]:
    if not path.exists():
        return []
    entries: List[IntentMismatchLogEntry] = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                continue
            ts = _parse_timestamp(data.get("timestamp"))
            if since is not None and ts is not None and ts < since:
                continue
            entries.append(
                IntentMismatchLogEntry(
                    text=data.get("text", ""),
                    expected_intent=data.get("expected_intent", ""),
                    actual_intent=data.get("actual_intent", ""),
                    lang=data.get("lang"),
                    source=data.get("source", "unknown"),
                    timestamp=data.get("timestamp", ""),
                    extra=data.get("extra") or {},
                )
            )
            if limit is not None and len(entries) >= limit:
                break
    return entries


__all__ = [
    "IntentMismatchLogEntry",
    "INTENT_MISMATCH_LOG_PATH",
    "log_intent_mismatch",
    "load_intent_mismatch_logs",
    "configure_intent_log_limit",
]


def _parse_timestamp(value: object) -> Optional[datetime]:
    if not value or not isinstance(value, str):
        return None
    cleaned = value.strip()
    if not cleaned:
        return None
    if cleaned.endswith("Z"):
        cleaned = cleaned[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(cleaned)
    except ValueError:
        return None
