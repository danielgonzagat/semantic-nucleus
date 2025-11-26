"""Auto-evolve frame patterns based on mismatch logs."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

from ..mismatch_logger import DEFAULT_LOG_FILE

FRAMES_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "frames_config.json"


@dataclass
class FrameMismatch:
    text: str
    expected_frame_id: str
    predicted_frame_type: str
    extra: Dict[str, Any]


def _load_frame_mismatches(log_path: Path = DEFAULT_LOG_FILE) -> List[FrameMismatch]:
    if not log_path.exists():
        return []
    mismatches: List[FrameMismatch] = []
    with log_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            data = json.loads(line)
            if data.get("kind") != "semantics":
                continue
            extra = data.get("extra", {})
            if extra.get("type") != "frame":
                continue
            mismatches.append(
                FrameMismatch(
                    text=data.get("text", ""),
                    expected_frame_id=data.get("expected", ""),
                    predicted_frame_type=data.get("predicted", ""),
                    extra=extra,
                )
            )
    return mismatches


def _load_frames_config() -> Dict[str, Any]:
    if not FRAMES_CONFIG_PATH.exists():
        return {"frames": []}
    return json.loads(FRAMES_CONFIG_PATH.read_text(encoding="utf-8"))


def _save_frames_config(cfg: Dict[str, Any]) -> None:
    FRAMES_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    FRAMES_CONFIG_PATH.write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def auto_evolve_frames() -> Dict[str, Any]:
    mismatches = _load_frame_mismatches()
    if not mismatches:
        return {"updated": False, "reason": "no frame mismatches"}

    cfg = _load_frames_config()
    frames: List[Dict[str, Any]] = cfg.get("frames", [])
    by_id = {frame["id"]: frame for frame in frames if "id" in frame}

    updated = False
    added: Dict[str, List[str]] = {}

    for mismatch in mismatches:
        fid = mismatch.expected_frame_id
        if not fid:
            continue
        frame = by_id.get(fid)
        if frame is None:
            frame = {"id": fid, "label": fid, "language": "pt", "patterns": [], "role_hints": {}}
            frames.append(frame)
            by_id[fid] = frame
        patterns = frame.setdefault("patterns", [])
        sentence = mismatch.text.strip()
        if sentence and sentence not in patterns:
            patterns.append(sentence)
            added.setdefault(fid, []).append(sentence)
            updated = True

    if updated:
        cfg["frames"] = frames
        _save_frames_config(cfg)

    return {"updated": updated, "added": added}


if __name__ == "__main__":
    print(auto_evolve_frames())
