"""
Auto-patch para frame_patterns.json com base em frame_mismatch.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple

from metanucleus.evolution.diff_utils import make_unified_diff
from metanucleus.evolution.types import EvolutionPatch
from metanucleus.utils.project import get_project_root

_ROOT = get_project_root(Path(__file__))
_LOG_PATH = _ROOT / ".metanucleus" / "mismatch_log.jsonl"
_PATTERNS_PATH = _ROOT / ".metanucleus" / "frame_patterns.json"


@dataclass()
class FramePattern:
    language: str
    predicate: str
    roles: Dict[str, List[str]]


def _normalize_lexeme(text: str) -> str:
    return text.strip().lower()


def _load_patterns() -> List[FramePattern]:
    if not _PATTERNS_PATH.exists():
        return []
    data = json.loads(_PATTERNS_PATH.read_text(encoding="utf-8"))
    frames = []
    for record in data.get("frames", []):
        frames.append(
            FramePattern(
                language=record.get("language", "unknown"),
                predicate=record.get("predicate", ""),
                roles={k: list(v) for k, v in record.get("roles", {}).items()},
            )
        )
    return frames


def _save_patterns(patterns: List[FramePattern]) -> str:
    payload = {
        "frames": [
            {
                "language": p.language,
                "predicate": p.predicate,
                "roles": p.roles,
            }
            for p in sorted(patterns, key=lambda item: (item.language, item.predicate))
        ]
    }
    _PATTERNS_PATH.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(payload, ensure_ascii=False, indent=2)
    _PATTERNS_PATH.write_text(serialized, encoding="utf-8")
    return serialized


def _index_patterns(patterns: List[FramePattern]) -> Dict[Tuple[str, str], FramePattern]:
    idx: Dict[Tuple[str, str], FramePattern] = {}
    for pattern in patterns:
        idx[(pattern.language, pattern.predicate)] = pattern
    return idx


def _load_frame_mismatches() -> List[Dict[str, Any]]:
    if not _LOG_PATH.exists():
        return []
    entries: List[Dict[str, Any]] = []
    with _LOG_PATH.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            if record.get("type") == "frame_mismatch":
                entries.append(record)
    return entries


def suggest_frame_patches() -> List[EvolutionPatch]:
    mismatches = _load_frame_mismatches()
    if not mismatches:
        return []

    patterns = _load_patterns()
    index = _index_patterns(patterns)

    new_patterns = 0
    updated_roles = 0

    for record in mismatches:
        language = str(record.get("language") or "unknown").strip()
        predicate = str(record.get("predicate") or "").strip() or "(unknown)"
        expected_roles = record.get("expected_roles") or {}

        key = (language, predicate)
        if key not in index:
            pattern = FramePattern(language=language, predicate=predicate, roles={})
            index[key] = pattern
            patterns.append(pattern)
            new_patterns += 1
        else:
            pattern = index[key]

        for role_name, expected_value in expected_roles.items():
            if not expected_value:
                continue
            normalized = _normalize_lexeme(expected_value)
            role_list = pattern.roles.setdefault(role_name, [])
            if normalized not in map(_normalize_lexeme, role_list):
                role_list.append(expected_value)
                updated_roles += 1

    original_text = (
        _PATTERNS_PATH.read_text(encoding="utf-8") if _PATTERNS_PATH.exists() else ""
    )
    updated_text = _save_patterns(patterns)

    if updated_text == original_text:
        return []

    rel_path = _PATTERNS_PATH.relative_to(_ROOT)
    diff = make_unified_diff(str(rel_path), original=original_text, patched=updated_text)

    return [
        EvolutionPatch(
            domain="semantic_frames",
            title="Atualizar frame_patterns",
            description=(
                "Acrescenta pistas de frames extraídas de frame_mismatch para "
                "melhorar o parser semântico."
            ),
            diff=diff,
            meta={
                "new_patterns": new_patterns,
                "updated_roles": updated_roles,
                "mismatches": len(mismatches),
            },
        )
    ]


__all__ = ["suggest_frame_patches"]
