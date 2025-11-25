"""
Meta-Reflexão determinística: árvore de justificativas e fases cognitivas.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import blake2b
from typing import Iterable, List, Optional, Tuple

from liu import Node, NodeKind, struct, text, list_node, entity, fingerprint, number


@dataclass(frozen=True)
class JustificationNode:
    """Nó da árvore de justificativa."""

    id: str
    type: str  # FACT, OPERATION, INFERENCE, RESOLUTION
    description: str
    dependencies: List["JustificationNode"]
    source_ref: Optional[Node] = None

    def to_liu(self) -> Node:
        """Converte recursivamente para LIU para ser retornado ao kernel."""
        deps_liu = [dep.to_liu() for dep in self.dependencies]
        fields = {
            "tag": entity("justification_node"),
            "id": text(self.id),
            "type": entity(self.type),
            "description": text(self.description),
            "dependencies": list_node(deps_liu),
        }
        if self.source_ref is not None:
            fields["source"] = self.source_ref
        return struct(**fields)


class MetaReflectionEngine:
    """
    Motor de meta-reflexão responsável por reconstruir árvores de justificativa
    a partir do contexto estrutural do NSR.
    """

    def __init__(self, meta_history: Iterable[Tuple[Node, ...]]):
        self.meta_history = list(meta_history)

    def build_justification_tree(
        self, answer_node: Node, context: Tuple[Node, ...]
    ) -> Optional[JustificationNode]:
        """
        Reconstrói a árvore de justificativa para uma resposta específica.
        """
        for node in context:
            if self._is_resolution_for(node, answer_node):
                return self._build_resolution_tree(node)
        for node in context:
            if self._is_proof_for(node):
                return self._build_proof_tree(node)
        return None

    def _is_resolution_for(self, resolution_node: Node, answer_node: Node) -> bool:
        if resolution_node.kind is not NodeKind.STRUCT:
            return False
        fields = dict(resolution_node.fields)
        tag = fields.get("tag")
        if not tag or (tag.label or "").lower() != "resolution":
            return False
        selected = fields.get("selected")
        if selected is None:
            return False
        return fingerprint(selected) == fingerprint(answer_node)

    def _is_proof_for(self, proof_node: Node) -> bool:
        if proof_node.kind is not NodeKind.STRUCT:
            return False
        fields = dict(proof_node.fields)
        tag = fields.get("tag")
        return bool(tag and (tag.label or "").lower() == "logic_proof")

    def _build_resolution_tree(self, resolution_node: Node) -> JustificationNode:
        fields = dict(resolution_node.fields)
        term = (fields.get("term").label if fields.get("term") else "") or "?"
        score_node = fields.get("score")
        score = score_node.value if score_node and score_node.value is not None else 0.0
        description = f"Termo '{term}' resolvido com score {score:.2f}"
        return JustificationNode(
            id=fingerprint(resolution_node),
            type="RESOLUTION",
            description=description,
            dependencies=[],
            source_ref=resolution_node,
        )

    def _build_proof_tree(self, proof_node: Node) -> JustificationNode:
        fields = dict(proof_node.fields)
        query = (fields.get("query").label if fields.get("query") else "") or "?"
        truth = (fields.get("truth").label if fields.get("truth") else "") or "unknown"
        facts_node = fields.get("facts")
        dependencies: List[JustificationNode] = []
        if facts_node and facts_node.kind is NodeKind.LIST:
            for fact in facts_node.args:
                label = ""
                if fact.kind is NodeKind.STRUCT:
                    fact_fields = dict(fact.fields)
                    statement = fact_fields.get("statement")
                    if statement and statement.label:
                        label = statement.label
                description = label or "Fact"
                dependencies.append(
                    JustificationNode(
                        id=fingerprint(fact),
                        type="FACT",
                        description=description,
                        dependencies=[],
                        source_ref=fact,
                    )
                )
        return JustificationNode(
            id=fingerprint(proof_node),
            type="LOGIC_PROOF",
            description=f"Prova lógica para '{query}': {truth}",
            dependencies=dependencies,
            source_ref=proof_node,
        )


# --------------------------------------------------------------------------- #
# Meta-Reflexão baseada no trace Φ                                             #
# --------------------------------------------------------------------------- #

_PHASE_LABELS = {
    "meta_ler": "Meta-LER",
    "meta_plan": "Meta-PLANO",
    "meta_phi": "Meta-PENSAR",
    "meta_memory": "Meta-MEMÓRIA",
    "meta_meta": "Meta-META",
    "meta_code": "Meta-CÓDIGO",
    "meta_guard": "Meta-GUARDA",
    "meta_halt": "Meta-HALT",
    "meta_misc": "Meta-MISC",
}

_LER_PREFIXES = (
    "TEXT[",
    "LOGIC[",
    "MATH[",
    "CODE[",
    "INSTINCT[",
    "IAN[",
    "COMMAND_",
    "STATE_",
    "FACT_",
    "QUERY",
    "LANG[",
)

_ALERT_TOKENS = ("CONTRADICTION", "FAILURE", "INVARIANT", "INV[", "ALERT")


@dataclass(slots=True)
class _ReflectionDecision:
    index: int
    label: str
    category: str
    title: str
    quality: Optional[float]
    relations: Optional[int]
    delta_quality: Optional[float]
    delta_relations: Optional[int]
    context: Optional[int]
    justification: str
    alert: bool = False


@dataclass(slots=True)
class _ReflectionPhase:
    name: str
    title: str
    order: int
    decisions: List[_ReflectionDecision] = field(default_factory=list)
    alert: bool = False
    enter_quality: Optional[float] = None
    exit_quality: Optional[float] = None
    enter_relations: Optional[int] = None
    exit_relations: Optional[int] = None

    def add(self, decision: _ReflectionDecision) -> None:
        self.decisions.append(decision)
        if self.enter_quality is None and decision.quality is not None:
            self.enter_quality = decision.quality
        if decision.quality is not None:
            self.exit_quality = decision.quality
        if self.enter_relations is None and decision.relations is not None:
            self.enter_relations = decision.relations
        if decision.relations is not None:
            self.exit_relations = decision.relations
        self.alert = self.alert or decision.alert or self.name == "meta_guard"


def build_meta_reflection(reasoning: Node | None) -> Node | None:
    """
    Constrói uma visão estruturada (meta_reflection) a partir do meta_reasoning.
    """

    operations = _extract_reasoning_operations(reasoning)
    decisions = [_decision_from_step(step) for step in operations]
    decisions = [decision for decision in decisions if decision is not None]
    if not decisions:
        return None
    phases = _build_phases(decisions)
    if not phases:
        return None
    digest = _reflection_digest(decisions)
    phase_chain = " → ".join(phase.title for phase in phases)
    dominant = max(phases, key=lambda phase: len(phase.decisions))
    alert_phase_nodes = [
        entity(phase.name) for phase in phases if phase.alert and phase.decisions
    ]
    fields = {
        "tag": entity("meta_reflection"),
        "phase_count": number(len(phases)),
        "decision_count": number(len(decisions)),
        "phase_chain": text(phase_chain),
        "dominant_phase": entity(dominant.name),
        "digest": text(digest),
        "phases": list_node([_phase_to_node(phase) for phase in phases]),
    }
    if alert_phase_nodes:
        fields["alert_phases"] = list_node(alert_phase_nodes)
    return struct(**fields)


# --------------------------------------------------------------------------- #
# Helpers                                                                     #
# --------------------------------------------------------------------------- #


def _extract_reasoning_operations(reasoning: Node | None) -> List[Node]:
    if reasoning is None or reasoning.kind is not NodeKind.STRUCT:
        return []
    fields = dict(reasoning.fields)
    ops_node = fields.get("operations")
    if ops_node is None or ops_node.kind is not NodeKind.LIST:
        return []
    return [
        op for op in ops_node.args if op.kind is NodeKind.STRUCT and op.fields
    ]


def _decision_from_step(step: Node) -> Optional[_ReflectionDecision]:
    fields = dict(step.fields)
    index = _node_int(fields.get("index")) or 0
    label_node = fields.get("label")
    label = (label_node.label if label_node else "") or f"STEP_{index}"
    quality = _node_float(fields.get("quality"))
    relations = _node_int(fields.get("relations"))
    delta_quality = _node_float(fields.get("delta_quality"))
    delta_relations = _node_int(fields.get("delta_relations"))
    context = _node_int(fields.get("context"))
    category, title = _classify_phase(label)
    justification = _decision_justification(
        label,
        quality,
        relations,
        delta_quality,
        delta_relations,
        context,
    )
    alert = _is_alert_label(label)
    return _ReflectionDecision(
        index=index,
        label=label,
        category=category,
        title=title,
        quality=quality,
        relations=relations,
        delta_quality=delta_quality,
        delta_relations=delta_relations,
        context=context,
        justification=justification,
        alert=alert,
    )


def _build_phases(decisions: List[_ReflectionDecision]) -> List[_ReflectionPhase]:
    phases: List[_ReflectionPhase] = []
    current: Optional[_ReflectionPhase] = None
    for decision in decisions:
        if current is None or decision.category != current.name:
            current = _ReflectionPhase(
                name=decision.category,
                title=decision.title,
                order=len(phases) + 1,
            )
            phases.append(current)
        current.add(decision)
    return phases


def _phase_to_node(phase: _ReflectionPhase) -> Node:
    decision_nodes = [_decision_to_node(decision) for decision in phase.decisions]
    fields = {
        "tag": entity("reflection_phase"),
        "name": entity(phase.name),
        "title": text(phase.title),
        "order": number(phase.order),
        "decision_count": number(len(phase.decisions)),
        "decisions": list_node(decision_nodes),
        "start_index": number(phase.decisions[0].index),
        "end_index": number(phase.decisions[-1].index),
    }
    if phase.enter_quality is not None:
        fields["enter_quality"] = number(phase.enter_quality)
    if phase.exit_quality is not None:
        fields["exit_quality"] = number(phase.exit_quality)
    if (
        phase.enter_quality is not None
        and phase.exit_quality is not None
        and phase.exit_quality != phase.enter_quality
    ):
        fields["quality_delta"] = number(phase.exit_quality - phase.enter_quality)
    if phase.enter_relations is not None:
        fields["enter_relations"] = number(phase.enter_relations)
    if phase.exit_relations is not None:
        fields["exit_relations"] = number(phase.exit_relations)
    if (
        phase.enter_relations is not None
        and phase.exit_relations is not None
        and phase.exit_relations != phase.enter_relations
    ):
        fields["relations_delta"] = number(phase.exit_relations - phase.enter_relations)
    if phase.alert:
        fields["alert"] = entity("true")
    summary = _phase_summary(phase)
    if summary:
        fields["summary"] = text(summary)
    return struct(**fields)


def _decision_to_node(decision: _ReflectionDecision) -> Node:
    fields = {
        "tag": entity("reflection_decision"),
        "index": number(decision.index),
        "label": entity(decision.label),
        "category": entity(decision.category),
        "justification": text(decision.justification),
    }
    if decision.quality is not None:
        fields["quality"] = number(decision.quality)
    if decision.relations is not None:
        fields["relations"] = number(decision.relations)
    if decision.delta_quality is not None:
        fields["delta_quality"] = number(decision.delta_quality)
    if decision.delta_relations is not None:
        fields["delta_relations"] = number(decision.delta_relations)
    if decision.context is not None:
        fields["context"] = number(decision.context)
    if decision.alert:
        fields["alert"] = entity("true")
    return struct(**fields)


def _phase_summary(phase: _ReflectionPhase) -> str:
    entries = len(phase.decisions)
    parts = [f"{phase.title} executou {entries} decisão(ões)"]
    if phase.enter_quality is not None and phase.exit_quality is not None:
        parts.append(f"q {phase.enter_quality:.2f}→{phase.exit_quality:.2f}")
    if phase.enter_relations is not None and phase.exit_relations is not None:
        parts.append(f"rel {phase.enter_relations}->{phase.exit_relations}")
    return " · ".join(parts)


def _decision_justification(
    label: str,
    quality: Optional[float],
    relations: Optional[int],
    delta_quality: Optional[float],
    delta_relations: Optional[int],
    context: Optional[int],
) -> str:
    metrics: List[str] = []
    if quality is not None:
        metrics.append(f"q={quality:.2f}")
    if delta_quality is not None:
        metrics.append(f"Δq={delta_quality:+.2f}")
    if relations is not None:
        metrics.append(f"rel={relations}")
    if delta_relations is not None:
        metrics.append(f"Δrel={delta_relations:+d}")
    if context is not None:
        metrics.append(f"ctx={context}")
    if metrics:
        return f"{label} · {', '.join(metrics)}"
    return label


def _classify_phase(label: str) -> Tuple[str, str]:
    upper = label.upper()
    predicates = (
        ("meta_guard", lambda value: any(token in value for token in _ALERT_TOKENS)),
        ("meta_halt", lambda value: value.startswith("HALT[")),
        (
            "meta_plan",
            lambda value: value.startswith("Φ_PLAN")
            or value.startswith("PHI_PLAN")
            or value.startswith("PLAN_ONLY"),
        ),
        ("meta_meta", lambda value: value.startswith("Φ_META") or value.startswith("PHI_META")),
        (
            "meta_code",
            lambda value: value.startswith("Φ_CODE")
            or value.startswith("PHI_CODE")
            or "CODE/" in value,
        ),
        (
            "meta_memory",
            lambda value: value.startswith("Φ_MEMORY")
            or value.startswith("PHI_MEMORY")
            or "MEMORY" in value,
        ),
        ("meta_phi", lambda value: value.startswith("Φ_") or value.startswith("PHI_")),
        ("meta_ler", lambda value: any(value.startswith(prefix) for prefix in _LER_PREFIXES)),
    )
    for category, predicate in predicates:
        if predicate(upper):
            return category, _PHASE_LABELS[category]
    return "meta_misc", _PHASE_LABELS["meta_misc"]


def _is_alert_label(label: str) -> bool:
    upper = label.upper()
    if any(token in upper for token in _ALERT_TOKENS):
        return True
    if upper.startswith("HALT[") and not upper.startswith("HALT[OPS_QUEUE_EMPTY]"):
        return True
    return False


def _reflection_digest(decisions: List[_ReflectionDecision]) -> str:
    hasher = blake2b(digest_size=16)
    for decision in decisions:
        hasher.update(f"{decision.index}:{decision.category}:{decision.label}".encode("utf-8"))
        if decision.quality is not None:
            hasher.update(f"q={decision.quality:.6f}".encode("utf-8"))
        if decision.delta_quality is not None:
            hasher.update(f"dq={decision.delta_quality:.6f}".encode("utf-8"))
        if decision.relations is not None:
            hasher.update(f"r={decision.relations}".encode("utf-8"))
        if decision.delta_relations is not None:
            hasher.update(f"dr={decision.delta_relations}".encode("utf-8"))
    return hasher.hexdigest()


def _node_float(node: Node | None) -> Optional[float]:
    if node is None or node.value is None:
        return None
    try:
        return float(node.value)
    except (TypeError, ValueError):
        return None


def _node_int(node: Node | None) -> Optional[int]:
    if node is None or node.value is None:
        return None
    try:
        return int(node.value)
    except (TypeError, ValueError):
        return None


__all__ = ["build_meta_reflection", "MetaReflectionEngine", "JustificationNode"]
