"""Auto-evolve intent patterns using mismatch logs."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

from ..mismatch_logger import DEFAULT_LOG_FILE

INTENT_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "intent_patterns.json"


@dataclass
class IntentMismatch:
    text: str
    expected: str
    predicted: str
    extra: Dict[str, Any]


def _load_mismatches(log_path: Path = DEFAULT_LOG_FILE) -> List[IntentMismatch]:
    if not log_path.exists():
        return []
    mismatches: List[IntentMismatch] = []
    with log_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            data = json.loads(line)
            if data.get("kind") != "intent":
                continue
            mismatches.append(
                IntentMismatch(
                    text=data.get("text", ""),
                    expected=data.get("expected", ""),
                    predicted=data.get("predicted", ""),
                    extra=data.get("extra", {}),
                )
            )
    return mismatches


def _load_patterns() -> Dict[str, List[str]]:
    if not INTENT_CONFIG_PATH.exists():
        return {}
    return json.loads(INTENT_CONFIG_PATH.read_text(encoding="utf-8"))


def _save_patterns(patterns: Dict[str, List[str]]) -> None:
    INTENT_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    INTENT_CONFIG_PATH.write_text(json.dumps(patterns, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def auto_evolve_intent_patterns() -> Dict[str, Any]:
    mismatches = _load_mismatches()
    if not mismatches:
        return {"updated": False, "reason": "no mismatches"}

    patterns = _load_patterns()
    updated = False
    added: Dict[str, List[str]] = {}

    for mismatch in mismatches:
        target = mismatch.expected
        if not target:
            continue
        sentence = mismatch.text.strip().lower()
        if len(sentence) < 2:
            continue
        bucket = patterns.setdefault(target, [])
        if sentence not in bucket:
            bucket.append(sentence)
            added.setdefault(target, []).append(sentence)
            updated = True

    if updated:
        _save_patterns(patterns)

    return {"updated": updated, "added": added}


if __name__ == "main":
    print(auto_evolve_intent_patterns())
