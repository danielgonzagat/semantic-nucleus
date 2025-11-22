from __future__ import annotations

import json
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Iterator

from nsr import RunOutcome


@dataclass(slots=True)
class Episode:
    text: str
    answer: str
    quality: float
    halt_reason: str
    trace_digest: str
    equation_hash: str
    contradictions: int
    timestamp: float
    kb_version: str | None = None

    @classmethod
    def from_outcome(
        cls,
        text: str,
        outcome: RunOutcome,
        kb_version: str | None = None,
    ) -> "Episode":
        trace = outcome.trace
        contradictions = len(getattr(trace, "contradictions", ()) or ())
        halt_reason = getattr(outcome.halt_reason, "name", str(outcome.halt_reason))
        return cls(
            text=text,
            answer=outcome.answer,
            quality=float(outcome.quality),
            halt_reason=str(halt_reason),
            trace_digest=str(trace.digest),
            equation_hash=str(outcome.equation_digest),
            contradictions=int(contradictions),
            timestamp=time.time(),
            kb_version=kb_version,
        )


def append_episode(path: Path, episode: Episode) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        json.dump(asdict(episode), handle, ensure_ascii=False, separators=(",", ":"))
        handle.write("\n")


def iter_episodes(path: Path) -> Iterator[dict[str, Any]]:
    if not path.exists():
        return
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                payload: dict[str, Any] = json.loads(line)
            except json.JSONDecodeError:
                continue
            yield payload
