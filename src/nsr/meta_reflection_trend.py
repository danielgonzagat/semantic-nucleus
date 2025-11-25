"""
Meta-Reflexão Temporal: gera tendências determinísticas a partir do histórico.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Sequence, Tuple

from liu import Node, NodeKind, entity, list_node, number, struct, text


@dataclass(frozen=True)
class _ReflectionSnapshot:
    digest: str
    phase_count: int
    decision_count: int
    dominant_phase: str
    alerts: Tuple[str, ...]


def build_reflection_trend(
    history: Sequence[Tuple[Node, ...]],
    current_reflection: Node | None,
    *,
    window: int = 8,
) -> Node | None:
    """
    Consolida as últimas reflexões (meta_reflection) em um nó `meta_reflection_trend`.
    """

    snapshots = list(_collect_snapshots(history[-window:]))
    if current_reflection is not None:
        snap = _snapshot_from_node(current_reflection)
        if snap is not None:
            snapshots.append(snap)
    if not snapshots:
        return None
    limited = snapshots[-window:]
    alert_entries = sum(1 for snap in limited if snap.alerts)
    alert_rate = alert_entries / len(limited)
    decision_avg = sum(snap.decision_count for snap in limited) / len(limited)
    first = limited[0]
    last = limited[-1]
    decision_delta = last.decision_count - first.decision_count
    trend_label = _trend_label(decision_delta)
    dominant_shift = "stable" if _all_equal(snap.dominant_phase for snap in limited) else "shifting"
    dominant_consistency = (
        sum(1 for snap in limited if snap.dominant_phase == last.dominant_phase) / len(limited)
    )
    history_nodes = _history_nodes(limited)
    fields = {
        "tag": entity("meta_reflection_trend"),
        "window": number(window),
        "entries": number(len(limited)),
        "trend": entity(trend_label),
        "alert_rate": number(round(alert_rate, 4)),
        "decision_avg": number(round(decision_avg, 4)),
        "decision_delta": number(decision_delta),
        "dominant_current": entity(last.dominant_phase or "unknown"),
        "dominant_shift": entity(dominant_shift),
        "dominant_consistency": number(round(dominant_consistency, 4)),
        "history": list_node(history_nodes),
    }
    return struct(**fields)


def _collect_snapshots(history: Iterable[Tuple[Node, ...]]) -> Iterable[_ReflectionSnapshot]:
    for summary in history:
        if summary is None:
            continue
        reflection = _find_reflection(summary)
        if reflection is None:
            continue
        snapshot = _snapshot_from_node(reflection)
        if snapshot is not None:
            yield snapshot


def _find_reflection(summary: Tuple[Node, ...]) -> Node | None:
    for node in summary:
        if node.kind is not NodeKind.STRUCT:
            continue
        fields = dict(node.fields)
        tag = fields.get("tag")
        if tag and (tag.label or "").lower() == "meta_reflection":
            return node
    return None


def _snapshot_from_node(reflection: Node) -> _ReflectionSnapshot | None:
    if reflection.kind is not NodeKind.STRUCT:
        return None
    fields = dict(reflection.fields)
    digest_node = fields.get("digest")
    phase_node = fields.get("phase_count")
    decision_node = fields.get("decision_count")
    dominant_node = fields.get("dominant_phase")
    alert_node = fields.get("alert_phases")
    digest = (digest_node.label if digest_node else "") or ""
    phase_count = _node_int(phase_node)
    decision_count = _node_int(decision_node)
    dominant_phase = _label(dominant_node)
    alerts = tuple(_extract_alerts(alert_node))
    return _ReflectionSnapshot(
        digest=digest,
        phase_count=phase_count,
        decision_count=decision_count,
        dominant_phase=dominant_phase,
        alerts=alerts,
    )


def _history_nodes(snapshots: Sequence[_ReflectionSnapshot]) -> List[Node]:
    nodes: List[Node] = []
    for idx, snap in enumerate(snapshots, start=1):
        entry_fields = {
            "tag": entity("reflection_trend_entry"),
            "index": number(idx),
            "digest": text(snap.digest),
            "phase_count": number(snap.phase_count),
            "decision_count": number(snap.decision_count),
            "dominant_phase": entity(snap.dominant_phase or "unknown"),
        }
        if snap.alerts:
            entry_fields["alerts"] = list_node([entity(label) for label in snap.alerts])
        nodes.append(struct(**entry_fields))
    return nodes


def _trend_label(decision_delta: int) -> str:
    if decision_delta >= 2:
        return "expanding"
    if decision_delta <= -2:
        return "contracting"
    if decision_delta == 0:
        return "stable"
    return "adjusting"


def _extract_alerts(node: Node | None) -> List[str]:
    if node is None:
        return []
    if node.kind is NodeKind.LIST:
        return [entry.label or "" for entry in node.args if entry.label]
    if node.label:
        return [node.label]
    return []


def _label(node: Node | None) -> str:
    if node is None:
        return ""
    return node.label or ""


def _node_int(node: Node | None) -> int:
    if node is None or node.value is None:
        return 0
    try:
        return int(node.value)
    except (TypeError, ValueError):
        return 0


def _all_equal(values: Iterable[str]) -> bool:
    iterator = iter(values)
    try:
        first = next(iterator)
    except StopIteration:
        return True
    return all(value == first for value in iterator)


__all__ = ["build_reflection_trend"]
