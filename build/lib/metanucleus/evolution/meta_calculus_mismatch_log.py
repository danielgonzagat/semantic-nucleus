"""
Logger determinístico de mismatches do meta-cálculo.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from metanucleus.utils.project import get_project_root

_PROJECT_ROOT = get_project_root(Path(__file__))
_META_DIR = _PROJECT_ROOT / ".meta"
_META_DIR.mkdir(parents=True, exist_ok=True)
META_CALCULUS_MISMATCH_LOG_PATH = _META_DIR / "meta_calculus_mismatches.jsonl"


@dataclass(slots=True)
class MetaCalculusMismatchEntry:
    test_id: str
    expr: str
    expected_repr: str
    actual_repr: str
    error_type: str = "value_mismatch"
    meta: Dict[str, Any] | None = None
    timestamp: str = ""

    def to_json(self) -> str:
        payload = asdict(self)
        payload["timestamp"] = payload["timestamp"] or datetime.now(timezone.utc).isoformat()
        return json.dumps(payload, ensure_ascii=False)


def log_meta_calculus_mismatch(
    *,
    test_id: str,
    expr: str,
    expected_repr: str,
    actual_repr: str,
    error_type: str = "value_mismatch",
    meta: Optional[Dict[str, Any]] = None,
    path: Path = META_CALCULUS_MISMATCH_LOG_PATH,
) -> None:
    entry = MetaCalculusMismatchEntry(
        test_id=test_id,
        expr=expr,
        expected_repr=expected_repr,
        actual_repr=actual_repr,
        error_type=error_type,
        meta=meta or {},
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(entry.to_json() + "\n")


def load_meta_calculus_mismatches(
    path: Path = META_CALCULUS_MISMATCH_LOG_PATH,
    limit: Optional[int] = None,
) -> List[MetaCalculusMismatchEntry]:
    if not path.exists():
        return []
    entries: List[MetaCalculusMismatchEntry] = []
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
                MetaCalculusMismatchEntry(
                    test_id=data.get("test_id", ""),
                    expr=data.get("expr", ""),
                    expected_repr=data.get("expected_repr", ""),
                    actual_repr=data.get("actual_repr", ""),
                    error_type=data.get("error_type", "value_mismatch"),
                    meta=data.get("meta") or {},
                    timestamp=data.get("timestamp", ""),
                )
            )
            if limit is not None and len(entries) >= limit:
                break
    return entries


__all__ = [
    "MetaCalculusMismatchEntry",
    "META_CALCULUS_MISMATCH_LOG_PATH",
    "log_meta_calculus_mismatch",
    "load_meta_calculus_mismatches",
]
