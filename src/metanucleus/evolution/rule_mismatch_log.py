"""
Registro determinístico de mismatches de regras/ontologia.
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
_LOGS_DIR = _PROJECT_ROOT / "logs"
_LOGS_DIR.mkdir(parents=True, exist_ok=True)
RULE_MISMATCH_LOG_PATH = _LOGS_DIR / "rule_mismatches.jsonl"
MAX_RULE_LOG_LINES_DEFAULT = 5000
_MAX_RULE_LOG_LINES = MAX_RULE_LOG_LINES_DEFAULT


@dataclass(slots=True)
class RuleMismatch:
    rule_name: str
    description: str
    context: str
    expected: str
    got: str
    severity: str = "warning"
    file_path: str = ""
    extra: Dict[str, Any] | None = None
    timestamp: str = ""


def append_rule_mismatch(entry: RuleMismatch, path: Path = RULE_MISMATCH_LOG_PATH) -> None:
    payload = asdict(entry)
    payload["timestamp"] = payload["timestamp"] or datetime.now(timezone.utc).isoformat()
    payload["extra"] = payload.get("extra") or {}
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(payload, ensure_ascii=False) + "\n")
    enforce_log_limit(path, _MAX_RULE_LOG_LINES)


def load_rule_mismatches(path: Path = RULE_MISMATCH_LOG_PATH, limit: Optional[int] = None) -> List[RuleMismatch]:
    if not path.exists():
        return []
    entries: List[RuleMismatch] = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                continue
            entries.append(
                RuleMismatch(
                    rule_name=data.get("rule_name", ""),
                    description=data.get("description", ""),
                    context=data.get("context", ""),
                    expected=data.get("expected", ""),
                    got=data.get("got", ""),
                    severity=data.get("severity", "warning"),
                    file_path=data.get("file_path", ""),
                    extra=data.get("extra") or {},
                    timestamp=data.get("timestamp", ""),
                )
            )
            if limit is not None and len(entries) >= limit:
                break
    return entries


__all__ = ["RuleMismatch", "append_rule_mismatch", "load_rule_mismatches", "RULE_MISMATCH_LOG_PATH"]


def configure_rule_log_limit(limit: int | None) -> None:
    global _MAX_RULE_LOG_LINES
    if limit is None or limit <= 0:
        _MAX_RULE_LOG_LINES = MAX_RULE_LOG_LINES_DEFAULT
    else:
        _MAX_RULE_LOG_LINES = limit
