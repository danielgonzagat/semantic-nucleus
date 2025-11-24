"""
Meta-Reflexão: constrói árvores determinísticas de justificativa por fase Φ.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import blake2b
from typing import List, Sequence

from liu import (
    Node,
    NodeKind,
    entity,
    list_node,
    number,
    struct as liu_struct,
    text as liu_text,
)


@dataclass(slots=True)
class _OperationEntry:
    order: int
    label: str
    quality: float | None
    delta_quality: float | None
    relations: int | None
    delta_relations: int | None
    context: int | None


@dataclass(slots=True)
class _ReflectionDecision:
    order: int
    label: str
    category: str
    justification: str
    quality: float | None
    delta_quality: float | None
    relations: int | None
    delta_relations: int | None
    context: int | None


@dataclass(slots=True)
class _ReflectionPhase:
    name: str
    order: int
    decisions: list[_ReflectionDecision]
    enter_quality: float | None = None
    exit_quality: float | None = None
    enter_relations: int | None = None
    exit_relations: int | None = None
    delta_quality: float = 0.0
    delta_relations: int = 0
    alert: bool = False

    def add(self, decision: _ReflectionDecision) -> None:
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
        if _is_alert_decision(decision):
            self.alert = True


_PHASE_LABELS = {
    "meta_ler": "Meta-LER",
    "meta_plan": "Meta-PLANO",
    "meta_code": "Meta-CÓDIGO",
    "meta_memory": "Meta-MEMÓRIA",
    "meta_phi": "Meta-PENSAR",
    "meta_meta": "Meta-META",
    "meta_guard": "Meta-GUARDA",
    "meta_halt": "Meta-HALT",
    "meta_misc": "Meta-MISC",
}


_CATEGORY_JUSTIFICATION = {
    "meta_ler": "Rota inicial detectada pelo Meta-LER.",
    "meta_plan": "Plano Φ configurado para guiar o cálculo.",
    "meta_code": "Operador Φ específico para ASTs ou código.",
    "meta_memory": "Memória simbólica foi reativada ou vinculada.",
    "meta_phi": "Operador Φ executado no loop principal.",
    "meta_meta": "Operador meta-analítico aplicado ao trace.",
    "meta_guard": "Guarda estrutural detectou inconsistências.",
    "meta_halt": "Execução convergiu e produziu um halt determinístico.",
    "meta_misc": "Entrada fora das categorias principais do trace.",
}


def build_meta_reflection(reasoning: Node | None) -> Node | None:
    """
    Constrói um nó LIU `meta_reflection` a partir de `meta_reasoning`.
    """

    operations = _extract_operations(reasoning)
    if not operations:
        return None
    decisions = [_decision_from_operation(op) for op in operations]
    phases = _build_phases(decisions)
    phase_nodes = [_phase_to_node(phase) for phase in phases]
    digest = _reflection_digest(decisions, phases)
    dominant = _dominant_phase(phases)
    chain = _phase_chain(phases)
    alert_names = [phase.name for phase in phases if phase.alert]
    fields: dict[str, Node] = {
        "tag": entity("meta_reflection"),
        "decision_count": number(len(decisions)),
        "phase_count": number(len(phases)),
        "phase_chain": liu_text(chain),
        "digest": liu_text(digest),
        "phases": list_node(phase_nodes),
    }
    if dominant is not None:
        fields["dominant_phase"] = entity(dominant.name)
    if alert_names:
        fields["alert_phases"] = list_node(entity(name) for name in alert_names)
    return liu_struct(**fields)


def _extract_operations(reasoning: Node | None) -> List[_OperationEntry]:
    if reasoning is None or reasoning.kind is not NodeKind.STRUCT:
        return []
    fields = dict(reasoning.fields)
    ops_node = fields.get("operations")
    if ops_node is None or ops_node.kind is not NodeKind.LIST:
        return []
    entries: List[_OperationEntry] = []
    for item in ops_node.args:
        if item.kind is not NodeKind.STRUCT:
            continue
        entry_fields = dict(item.fields)
        index_node = entry_fields.get("index")
        label_node = entry_fields.get("label")
        if index_node is None or label_node is None:
            continue
        entries.append(
            _OperationEntry(
                order=int(index_node.value or 0),
                label=label_node.label or "",
                quality=_node_float(entry_fields.get("quality")),
                delta_quality=_node_float(entry_fields.get("delta_quality")),
                relations=_node_int(entry_fields.get("relations")),
                delta_relations=_node_int(entry_fields.get("delta_relations")),
                context=_node_int(entry_fields.get("context")),
            )
        )
    entries.sort(key=lambda entry: entry.order)
    return entries


def _decision_from_operation(entry: _OperationEntry) -> _ReflectionDecision:
    category = _classify_category(entry.label)
    justification = _decision_justification(entry.label, category)
    return _ReflectionDecision(
        order=entry.order,
        label=entry.label,
        category=category,
        justification=justification,
        quality=entry.quality,
        delta_quality=entry.delta_quality,
        relations=entry.relations,
        delta_relations=entry.delta_relations,
        context=entry.context,
    )


def _build_phases(decisions: Sequence[_ReflectionDecision]) -> List[_ReflectionPhase]:
    phases: List[_ReflectionPhase] = []
    current: _ReflectionPhase | None = None
    for decision in decisions:
        if current is None or current.name != decision.category:
            current = _ReflectionPhase(name=decision.category, order=len(phases) + 1, decisions=[])
            phases.append(current)
        current.add(decision)
    return phases


def _phase_to_node(phase: _ReflectionPhase) -> Node:
    decisions = [_decision_to_node(decision) for decision in phase.decisions]
    fields: dict[str, Node] = {
        "tag": entity("reflection_phase"),
        "name": entity(phase.name),
        "label": entity(_PHASE_LABELS.get(phase.name, phase.name)),
        "order": number(phase.order),
        "decision_count": number(len(phase.decisions)),
        "decisions": list_node(decisions),
    }
    if phase.enter_quality is not None:
        fields["enter_quality"] = number(phase.enter_quality)
    if phase.exit_quality is not None:
        fields["exit_quality"] = number(phase.exit_quality)
    if phase.delta_quality:
        fields["delta_quality"] = number(round(float(phase.delta_quality), 6))
    if phase.enter_relations is not None:
        fields["enter_relations"] = number(phase.enter_relations)
    if phase.exit_relations is not None:
        fields["exit_relations"] = number(phase.exit_relations)
    if phase.delta_relations:
        fields["delta_relations"] = number(phase.delta_relations)
    if phase.alert:
        fields["alert"] = entity("true")
    return liu_struct(**fields)


def _decision_to_node(decision: _ReflectionDecision) -> Node:
    fields: dict[str, Node] = {
        "tag": entity("reflection_decision"),
        "order": number(decision.order),
        "label": entity(decision.label or f"STEP_{decision.order}"),
        "category": entity(decision.category),
        "justification": liu_text(decision.justification),
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


def _dominant_phase(phases: Sequence[_ReflectionPhase]) -> _ReflectionPhase | None:
    if not phases:
        return None
    return max(
        phases,
        key=lambda phase: (
            len(phase.decisions),
            abs(phase.delta_quality),
            phase.delta_relations,
            -phase.order,
        ),
    )


def _phase_chain(phases: Sequence[_ReflectionPhase]) -> str:
    if not phases:
        return ""
    labels = [_PHASE_LABELS.get(phase.name, phase.name) for phase in phases]
    return "→".join(labels)


def _reflection_digest(
    decisions: Sequence[_ReflectionDecision],
    phases: Sequence[_ReflectionPhase],
) -> str:
    hasher = blake2b(digest_size=16)
    for decision in decisions:
        hasher.update(f"{decision.order}:{decision.category}:{decision.label}".encode("utf-8"))
        if decision.delta_quality is not None:
            hasher.update(f"dq={decision.delta_quality:.6f}".encode("utf-8"))
        if decision.delta_relations is not None:
            hasher.update(f"dr={decision.delta_relations}".encode("utf-8"))
    for phase in phases:
        hasher.update(f"phase:{phase.name}:{len(phase.decisions)}".encode("utf-8"))
        if phase.alert:
            hasher.update(b"alert")
    return hasher.hexdigest()


def _classify_category(label: str) -> str:
    upper = (label or "").upper()
    if upper.startswith(("TEXT[", "LOGIC[", "MATH[", "IAN[")):
        return "meta_ler"
    if upper.startswith("Φ_PLAN") or upper.startswith("PLAN_ONLY"):
        return "meta_plan"
    if upper.startswith("Φ_CODE"):
        return "meta_code"
    if upper.startswith("Φ_MEMORY"):
        return "meta_memory"
    if upper.startswith("Φ_META"):
        return "meta_meta"
    if upper.startswith("Φ_"):
        return "meta_phi"
    if upper.startswith(("CONTRADICTION", "INV[")):
        return "meta_guard"
    if upper.startswith("HALT"):
        return "meta_halt"
    return "meta_misc"


def _decision_justification(label: str, category: str) -> str:
    base = _CATEGORY_JUSTIFICATION.get(category, _CATEGORY_JUSTIFICATION["meta_misc"])
    if category == "meta_plan" and "[" in label:
        plan = label.split("[", 1)[1].rstrip("]")
        return f"{base} Cadeia planejada: {plan}."
    if category == "meta_phi":
        return f"{base} Operador executado: {label}."
    if category == "meta_guard":
        return f"{base} Evento: {label}."
    if category == "meta_halt":
        return f"{base} Motivo: {label}."
    return base


def _is_alert_decision(decision: _ReflectionDecision) -> bool:
    upper = decision.label.upper()
    if decision.category == "meta_guard":
        return True
    return upper.startswith("CONTRADICTION") or "FAILURE" in upper


def _node_float(node: Node | None) -> float | None:
    if node is None or node.value is None:
        return None
    try:
        return float(node.value)
    except (TypeError, ValueError):
        return None


def _node_int(node: Node | None) -> int | None:
    if node is None or node.value is None:
        return None
    try:
        return int(node.value)
    except (TypeError, ValueError):
        return None


__all__ = ["build_meta_reflection"]
