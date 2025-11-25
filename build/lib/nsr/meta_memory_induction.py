"""
Memória longa + indução determinística de regras simbólicas.
"""

from __future__ import annotations

import json
import time
from collections import Counter
from pathlib import Path
from typing import Iterable, List, Tuple

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from nsr.runtime import RunOutcome  # pragma: no cover


def record_episode(path: str, text: str, outcome: RunOutcome) -> None:
    """
    Persiste um episódio (entrada + relações LIU) em JSONL determinístico.
    """

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "text": text,
        "quality": float(outcome.quality),
        "halt": getattr(outcome.halt_reason, "value", str(outcome.halt_reason)),
        "timestamp": time.time(),
        "relations": _extract_relations(outcome),
    }
    with target.open("a", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, separators=(",", ":"))
        handle.write("\n")


def run_memory_induction(
    episodes_path: str,
    suggestions_path: str,
    *,
    episode_limit: int,
    min_support: int,
) -> None:
    """
    Induz pares determinísticos de regras (rel→rel) com base na memória longa.
    """

    if not episodes_path or not suggestions_path:
        return
    episodes = _load_recent_records(Path(episodes_path), episode_limit)
    if not episodes:
        return
    cooc = Counter()
    for record in episodes:
        triples = _triples_from_relations(record.get("relations") or [])
        if not triples:
            continue
        unique = list(dict.fromkeys(triples))
        for i in range(len(unique)):
            for j in range(len(unique)):
                if i == j:
                    continue
                cooc[(unique[i], unique[j])] += 1
    if not cooc:
        return
    existing = _load_existing_suggestions(Path(suggestions_path))
    new_specs: List[dict] = []
    for (lhs, rhs), count in sorted(cooc.items(), key=lambda item: -item[1]):
        if count < max(1, min_support):
            continue
        key = (lhs[0], rhs[0])
        if key in existing:
            continue
        spec = {
            "if_rel": lhs[0],
            "then_rel": rhs[0],
            "support": int(count),
            "timestamp": time.time(),
            "source": "memory_induction",
        }
        existing.add(key)
        new_specs.append(spec)
    if not new_specs:
        return
    target = Path(suggestions_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a", encoding="utf-8") as handle:
        for spec in new_specs:
            json.dump(spec, handle, ensure_ascii=False, separators=(",", ":"))
            handle.write("\n")


def _extract_relations(outcome: RunOutcome) -> list[dict]:
    bundle = outcome.equation.to_json_bundle()
    rels = []
    for node in bundle.get("relations", []):
        if node.get("kind") != "REL":
            continue
        label = node.get("label") or ""
        if not label:
            continue
        args = []
        for arg in node.get("args", []):
            if isinstance(arg, dict) and arg.get("label"):
                args.append(arg["label"])
            elif isinstance(arg, dict) and arg.get("value") is not None:
                args.append(str(arg["value"]))
        rels.append({"rel": label, "args": args})
    return rels


def _triples_from_relations(rels: Iterable[dict]) -> list[Tuple[str, str, str]]:
    triples: list[Tuple[str, str, str]] = []
    for rel in rels:
        label = rel.get("rel") or ""
        args = rel.get("args") or []
        if len(args) >= 2:
            triples.append((label, str(args[0]), str(args[1])))
    return triples


def _load_recent_records(path: Path, limit: int) -> list[dict]:
    if limit <= 0 or not path.exists():
        return []
    with path.open("r", encoding="utf-8") as handle:
        lines = [line.strip() for line in handle if line.strip()]
    lines = lines[-limit:]
    records: list[dict] = []
    for line in lines:
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return records


def _load_existing_suggestions(path: Path) -> set[tuple[str, str]]:
    if not path.exists():
        return set()
    existing: set[tuple[str, str]] = set()
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            key = (payload.get("if_rel") or "", payload.get("then_rel") or "")
            existing.add(key)
    return existing


__all__ = ["record_episode", "run_memory_induction"]
