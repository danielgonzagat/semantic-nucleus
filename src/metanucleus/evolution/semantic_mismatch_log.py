"""
Registro determinístico de mismatches semânticos.
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
SEMANTIC_MISMATCH_LOG_PATH = _LOGS_DIR / "semantic_mismatches.jsonl"
MAX_SEMANTIC_LOG_LINES_DEFAULT = 5000
_MAX_SEMANTIC_LOG_LINES = MAX_SEMANTIC_LOG_LINES_DEFAULT


@dataclass(slots=True)
class SemanticMismatch:
    phrase: str
    lang: str
    issue: str
    expected_repr: str
    actual_repr: str
    severity: str = "warning"
    file_path: str = ""
    extra: Dict[str, Any] | None = None
    timestamp: str = ""


def append_semantic_mismatch(entry: SemanticMismatch, path: Path = SEMANTIC_MISMATCH_LOG_PATH) -> None:
    payload = asdict(entry)
    payload["timestamp"] = payload["timestamp"] or datetime.now(timezone.utc).isoformat()
    payload["extra"] = payload.get("extra") or {}
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(payload, ensure_ascii=False) + "\n")
    enforce_log_limit(path, _MAX_SEMANTIC_LOG_LINES)


def load_semantic_mismatches(path: Path = SEMANTIC_MISMATCH_LOG_PATH, limit: Optional[int] = None) -> List[SemanticMismatch]:
    if not path.exists():
        return []
    entries: List[SemanticMismatch] = []
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
                SemanticMismatch(
                    phrase=data.get("phrase", ""),
                    lang=data.get("lang", ""),
                    issue=data.get("issue", ""),
                    expected_repr=data.get("expected_repr", ""),
                    actual_repr=data.get("actual_repr", ""),
                    severity=data.get("severity", "warning"),
                    file_path=data.get("file_path", ""),
                    extra=data.get("extra") or {},
                    timestamp=data.get("timestamp", ""),
                )
            )
            if limit is not None and len(entries) >= limit:
                break
    return entries


__all__ = ["SemanticMismatch", "append_semantic_mismatch", "load_semantic_mismatches", "SEMANTIC_MISMATCH_LOG_PATH", "configure_semantic_log_limit"]


def configure_semantic_log_limit(limit: int | None) -> None:
    global _MAX_SEMANTIC_LOG_LINES
    if limit is None or limit <= 0:
        _MAX_SEMANTIC_LOG_LINES = MAX_SEMANTIC_LOG_LINES_DEFAULT
    else:
        _MAX_SEMANTIC_LOG_LINES = limit
