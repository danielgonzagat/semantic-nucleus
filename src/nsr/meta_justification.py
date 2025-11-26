"""
Meta-Justificativa: sintetiza a árvore lógica acessível de decisões Φ.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import blake2b
from typing import List, Sequence

from liu import (
    Node,
    entity,
    list_node,
    number,
    struct as liu_struct,
    text as liu_text,
)

from .meta_trace_utils import (
    TraceOperation,
    classify_trace_category,
    decision_justification,
    extract_trace_operations,
    is_alert_decision,
    phase_label,
    tree_depth,
)


@dataclass()
class _JustificationDecision:
    order: int
    label: str
    category: str
    reason: str
    quality: float | None
    delta_quality: float | None
    relations: int | None
    delta_relations: int | None
    context: int | None


@dataclass()
class _JustificationPhase:
    name: str
    order: int
    decisions: list[_JustificationDecision]
    enter_quality: float | None = None
    exit_quality: float | None = None
    enter_relations: int | None = None
    exit_relations: int | None = None
    delta_quality: float = 0.0
    delta_relations: int = 0
    alert: bool = False

    def add(self, decision: _JustificationDecision) -> None:
        self.decisions.append(decision)
        if decision.quality is not None:
            if self.enter_quality is None:
                self.enter_quality = decision.quality
            self.exit_quality = decision.quality
        if decision.delta_quality is not None:
            self.delta_quality += decision.delta_quality
        if decision.relations is not None:
            if self.enter_relations is None:
                self.enter_relations = decision.relations
            self.exit_relations = decision.relations
        if decision.delta_relations is not None:
            self.delta_relations += decision.delta_relations
        if is_alert_decision(decision.label, decision.category):
            self.alert = True


def build_meta_justification(reasoning: Node | None) -> Node | None:
    """
    Constrói um nó LIU `meta_justification` descrevendo a árvore de decisões Φ.
    """

    operations = extract_trace_operations(reasoning)
    if not operations:
        return None
    decisions = [_decision_from_operation(entry) for entry in operations]
    phases = _build_phases(decisions)
    if not phases:
        return None
    phase_nodes = [_phase_to_node(phase) for phase in phases]
    alert_names = [phase.name for phase in phases if phase.alert]
    digest = _tree_digest(phases)
    depth = tree_depth([phase.decisions for phase in phases])
    node_count = 1 + len(phases) + sum(len(phase.decisions) for phase in phases)
    root = liu_struct(
        tag=entity("justification_root"),
        label=entity("meta_pipeline"),
        order=number(0),
        impact=_impact_node(decisions),
        children=list_node(phase_nodes),
    )
    fields: dict[str, Node] = {
        "tag": entity("meta_justification"),
        "digest": liu_text(digest),
        "depth": number(depth),
        "width": number(len(phases)),
        "node_count": number(node_count),
        "root": root,
    }
    if alert_names:
        fields["alert_phases"] = list_node(entity(name) for name in alert_names)
    return liu_struct(**fields)


def _decision_from_operation(entry: TraceOperation) -> _JustificationDecision:
    category = classify_trace_category(entry.label)
    justification = decision_justification(entry.label, category)
    return _JustificationDecision(
        order=entry.order,
        label=entry.label,
        category=category,
        reason=justification,
        quality=entry.quality,
        delta_quality=entry.delta_quality,
        relations=entry.relations,
        delta_relations=entry.delta_relations,
        context=entry.context,
    )


def _build_phases(decisions: Sequence[_JustificationDecision]) -> List[_JustificationPhase]:
    phases: List[_JustificationPhase] = []
    current: _JustificationPhase | None = None
    for decision in decisions:
        if current is None or current.name != decision.category:
            current = _JustificationPhase(name=decision.category, order=len(phases) + 1, decisions=[])
            phases.append(current)
        current.add(decision)
    return phases


def _phase_to_node(phase: _JustificationPhase) -> Node:
    child_nodes = [_decision_to_node(decision) for decision in phase.decisions]
    fields: dict[str, Node] = {
        "tag": entity("justification_phase"),
        "name": entity(phase.name),
        "label": entity(phase_label(phase.name)),
        "order": number(phase.order),
        "step_count": number(len(phase.decisions)),
    }
    impact_fields = _phase_impact_fields(phase)
    if impact_fields:
        fields["impact"] = liu_struct(**impact_fields)
    fields["children"] = list_node(child_nodes) if child_nodes else list_node([])
    if phase.alert:
        fields["alert"] = entity("true")
    return liu_struct(**fields)


def _phase_impact_fields(phase: _JustificationPhase) -> dict[str, Node]:
    impact: dict[str, Node] = {}
    if phase.enter_quality is not None:
        impact["enter_quality"] = number(phase.enter_quality)
    if phase.exit_quality is not None:
        impact["exit_quality"] = number(phase.exit_quality)
    if phase.delta_quality:
        impact["delta_quality"] = number(round(float(phase.delta_quality), 6))
    if phase.enter_relations is not None:
        impact["enter_relations"] = number(phase.enter_relations)
    if phase.exit_relations is not None:
        impact["exit_relations"] = number(phase.exit_relations)
    if phase.delta_relations:
        impact["delta_relations"] = number(phase.delta_relations)
    return impact


def _decision_to_node(decision: _JustificationDecision) -> Node:
    fields: dict[str, Node] = {
        "tag": entity("justification_step"),
        "order": number(decision.order),
        "label": entity(decision.label or f"STEP_{decision.order}"),
        "category": entity(decision.category),
        "reason": liu_text(decision.reason),
    }
    if decision.quality is not None:
        fields["quality"] = number(decision.quality)
    if decision.delta_quality is not None:
        fields["delta_quality"] = number(decision.delta_quality)
    if decision.relations is not None:
        fields["relations"] = number(decision.relations)
    if decision.delta_relations is not None:
        fields["delta_relations"] = number(decision.delta_relations)
    if decision.context is not None:
        fields["context"] = number(decision.context)
    return liu_struct(**fields)


def _impact_node(decisions: Sequence[_JustificationDecision]) -> Node:
    total_delta_quality = round(
        sum(dec.delta_quality or 0.0 for dec in decisions),
        6,
    )
    total_delta_relations = sum(dec.delta_relations or 0 for dec in decisions)
    fields = {
        "tag": entity("justification_impact"),
        "delta_quality": number(total_delta_quality),
        "delta_relations": number(total_delta_relations),
    }
    return liu_struct(**fields)


def _tree_digest(phases: Sequence[_JustificationPhase]) -> str:
    hasher = blake2b(digest_size=16)
    for phase in phases:
        hasher.update(f"phase:{phase.name}:{len(phase.decisions)}".encode("utf-8"))
        hasher.update(f"dq={phase.delta_quality:.6f}".encode("utf-8"))
        hasher.update(f"dr={phase.delta_relations}".encode("utf-8"))
        if phase.alert:
            hasher.update(b"alert")
        for decision in phase.decisions:
            hasher.update(f"step:{decision.order}:{decision.category}:{decision.label}".encode("utf-8"))
            if decision.delta_quality is not None:
                hasher.update(f"dq={decision.delta_quality:.6f}".encode("utf-8"))
            if decision.delta_relations is not None:
                hasher.update(f"dr={decision.delta_relations}".encode("utf-8"))
    return hasher.hexdigest()


__all__ = ["build_meta_justification"]
