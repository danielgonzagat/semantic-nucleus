"""
Meta-Pensar: serializa o raciocínio Φ em estruturas LIU auditáveis.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import blake2b
from typing import Iterable, List

from liu import Node, entity, list_node, number, struct as liu_struct, text


@dataclass(slots=True)
class _ReasoningStep:
    index: int
    label: str
    quality: float | None
    relations: int | None
    context: int | None


def build_meta_reasoning(steps: Iterable[str], *, max_steps: int = 64) -> Node | None:
    """
    Constrói um nó LIU com o histórico das operações Φ executadas.
    """

    parsed_steps = _parse_steps(steps, max_steps=max_steps)
    if not parsed_steps:
        return None
    operations = []
    stats = {}
    digest_hasher = blake2b(digest_size=16)
    prev_quality: float | None = None
    prev_relations: int | None = None
    for entry in parsed_steps:
        digest_hasher.update(f"{entry.index}:{entry.label}".encode("utf-8"))
        if entry.quality is not None:
            digest_hasher.update(f"q={entry.quality:.5f}".encode("utf-8"))
        if entry.relations is not None:
            digest_hasher.update(f"r={entry.relations}".encode("utf-8"))
        if entry.context is not None:
            digest_hasher.update(f"c={entry.context}".encode("utf-8"))
        delta_quality: float | None = None
        delta_relations: int | None = None
        if entry.quality is not None:
            delta_quality = (
                round(entry.quality - (prev_quality or 0.0), 6)
                if prev_quality is not None
                else 0.0
            )
            prev_quality = entry.quality
        if entry.relations is not None:
            if prev_relations is not None:
                delta_relations = entry.relations - prev_relations
            else:
                delta_relations = 0
            prev_relations = entry.relations
        fields: dict[str, Node] = {
            "tag": entity("reasoning_step"),
            "index": number(entry.index),
            "label": entity(entry.label),
        }
        if entry.quality is not None:
            fields["quality"] = number(entry.quality)
        if delta_quality is not None:
            fields["delta_quality"] = number(delta_quality)
        if entry.relations is not None:
            fields["relations"] = number(entry.relations)
        if delta_relations is not None:
            fields["delta_relations"] = number(delta_relations)
        if entry.context is not None:
            fields["context"] = number(entry.context)
        operations.append(liu_struct(**fields))
        key = _operator_key(entry.label)
        stats[key] = stats.get(key, 0) + 1
    stats_nodes = [
        liu_struct(tag=entity("reasoning_stat"), label=entity(label), count=number(count))
        for label, count in sorted(stats.items())
    ]
    digest = digest_hasher.hexdigest()
    result_fields: dict[str, Node] = {
        "tag": entity("meta_reasoning"),
        "step_count": number(len(parsed_steps)),
        "digest": text(digest),
        "operations": list_node(operations),
    }
    if stats_nodes:
        result_fields["operator_stats"] = list_node(stats_nodes)
    return liu_struct(**result_fields)


def _parse_steps(steps: Iterable[str], *, max_steps: int) -> List[_ReasoningStep]:
    parsed: List[_ReasoningStep] = []
    for idx, raw in enumerate(steps):
        if idx >= max_steps:
            break
        entry = _parse_step(raw, fallback_index=idx + 1)
        if entry is not None:
            parsed.append(entry)
    return parsed


def _parse_step(raw: str, *, fallback_index: int) -> _ReasoningStep | None:
    text_line = (raw or "").strip()
    if not text_line:
        return None
    number_part, sep, remainder = text_line.partition(":")
    if sep:
        try:
            index = int(number_part)
        except ValueError:
            index = fallback_index
    else:
        index = fallback_index
        remainder = text_line
    remainder = remainder.strip()
    if not remainder:
        return _ReasoningStep(index=index, label=f"STEP_{index}", quality=None, relations=None, context=None)
    if " " in remainder:
        label_part, metrics_part = remainder.split(" ", 1)
    else:
        label_part, metrics_part = remainder, ""
    label = label_part.strip() or f"STEP_{index}"
    metrics = _extract_metrics(metrics_part)
    return _ReasoningStep(
        index=index,
        label=label,
        quality=_to_float(metrics.get("q")),
        relations=_to_int(metrics.get("rel")),
        context=_to_int(metrics.get("ctx")),
    )


def _extract_metrics(payload: str) -> dict[str, str]:
    metrics: dict[str, str] = {}
    for token in payload.replace(",", " ").split():
        if "=" not in token:
            continue
        key, value = token.split("=", 1)
        metrics[key.strip()] = value.strip()
    return metrics


def _to_float(value: str | None) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _to_int(value: str | None) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def _operator_key(label: str) -> str:
    base = label.strip()
    if "[" in base:
        return base.split("[", 1)[0].upper()
    if ":" in base:
        return base.split(":", 1)[0].upper()
    return base.upper()


__all__ = ["build_meta_reasoning"]
