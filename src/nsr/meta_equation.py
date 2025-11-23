"""
Construtores LIU para snapshots de Equação (meta-auditoria do ISR).
"""

from __future__ import annotations

from liu import Node, entity, number, struct as liu_struct, list_node, text as liu_text

from .equation import EquationSnapshot, EquationSnapshotStats

_SECTION_NAMES = ("ontology", "relations", "context", "goals", "ops_queue")
_DELTA_TOLERANCE = 1e-3


def build_meta_equation_node(
    snapshot: EquationSnapshot, previous: EquationSnapshotStats | None = None
) -> Node:
    """
    Serializa `EquationSnapshot` em um nó `meta_equation` auditável.
    Quando `previous` é informado, inclui deltas determinísticos.
    """

    stats = snapshot.stats()
    section_nodes = [
        liu_struct(
            tag=entity("equation_section"),
            name=entity(name),
            count=number(_section(stats, name).count),
            digest=liu_text(_section(stats, name).digest),
        )
        for name in _SECTION_NAMES
    ]
    fields: dict[str, Node] = {
        "tag": entity("meta_equation"),
        "digest": liu_text(stats.equation_digest),
        "input_digest": liu_text(stats.input_digest),
        "answer_digest": liu_text(stats.answer_digest),
        "quality": number(round(float(stats.quality), 6)),
        "sections": list_node(section_nodes),
        "trend": entity("initial"),
    }
    if previous is not None:
        delta_sections = []
        structural_delta = 0
        for name in _SECTION_NAMES:
            current_section = _section(stats, name)
            prev_section = _section(previous, name)
            delta_count = current_section.count - prev_section.count
            structural_delta += abs(delta_count)
            digest_changed = current_section.digest != prev_section.digest
            delta_sections.append(
                liu_struct(
                    tag=entity("equation_section_delta"),
                    name=entity(name),
                    delta_count=number(delta_count),
                    digest_changed=entity("true" if digest_changed else "false"),
                )
            )
        quality_delta = float(stats.quality - previous.quality)
        fields["delta_quality"] = number(round(quality_delta, 6))
        fields["delta_sections"] = list_node(delta_sections)
        trend = _classify_trend(quality_delta, structural_delta)
        fields["trend"] = entity(trend)
    return liu_struct(**fields)


def _section(stats: EquationSnapshotStats, name: str):
    return getattr(stats, name)


def _classify_trend(quality_delta: float, structural_delta: int) -> str:
    if quality_delta > _DELTA_TOLERANCE or structural_delta > 0:
        return "expanding"
    if quality_delta < -_DELTA_TOLERANCE:
        return "regressing"
    return "stable"


__all__ = ["build_meta_equation_node"]
