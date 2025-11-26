"""Structured mismatch logging utilities."""
from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, Literal
import json

MismatchKind = Literal["intent", "semantics", "calculus"]

DEFAULT_LOG_DIR = Path(".metanucleus")
DEFAULT_LOG_FILE = DEFAULT_LOG_DIR / "mismatch_log.jsonl"


@dataclass
class MismatchRecord:
    kind: MismatchKind
    text: str
    expected: str
    predicted: str
    extra: Dict[str, object]


def log_mismatch(record: MismatchRecord, logfile: Path = DEFAULT_LOG_FILE) -> None:
    logfile.parent.mkdir(parents=True, exist_ok=True)
    with logfile.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(asdict(record), ensure_ascii=False) + "\n")
