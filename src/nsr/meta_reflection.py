"""
Módulo de Justificativa Lógica e Árvore de Rastreabilidade.
Integra:
 - Árvore de Justificação (versão antiga)
 - Fases de Reflexão (nova)
 - Digest de meta_reflection (nova)
 - Compatibilidade com o kernel LIU
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple, Dict, Any, Sequence

# --- Imports do sistema LIU ---
from liu import (
    Node,
    entity,
    list_node,
    number,
    struct as liu_struct,
    text as liu_text,
)

# --- Imports do sistema de trace e reflexão nova ---
from .meta_trace_utils import (
    TraceOperation,
    classify_trace_category,
    decision_justification,
    extract_trace_operations,
    is_alert_decision,
    phase_label,
)

# --- Utilities adicionais ---
from hashlib import blake2b


# ============================================================
#     PARTE 1 — SISTEMA ANTIGO DE JUSTIFICATIVAS (LEGADO)
# ============================================================

@dataclass(frozen=True)
class JustificationNode:
    """Nó da árvore de justificativa (versão antiga, mantida para runtime)."""
    id: str
    type: str
    description: str
    dependencies: List["JustificationNode"]
    source_ref: Optional[Node] = None

    def to_liu(self) -> Node:
        deps_liu = [d.to_liu() for d in self.dependencies]
        return liu_struct(
            tag=entity("justification_node"),
            id=liu_text(self.id),
            type=entity(self.type),
            description=liu_text(self.description),
            dependencies=list_node(deps_liu)
        )


class MetaReflectionEngine:
    """
    Motor legado de reconstrução de justificativas.
    Mantido por compatibilidade, mas não interfere com o novo meta_reflection.
    """

    def __init__(self, trace: List[Tuple[Node, ...]]):
        self.trace = trace

    # ---------------------------------------------------------
    #  Métodos placeholder antigos — mantidos para compatibilidade
    # ---------------------------------------------------------
    def build_justification_tree(self, answer_node: Node, context: Tuple[Node, ...]) -> Optional[JustificationNode]:
        # Fallback simples — árvore linear
        return self._build_linear_trace_tree(context)

    def _build_linear_trace_tree(self, context: Tuple[Node, ...]) -> JustificationNode:
        desc = "Justificação linear criada automaticamente (compatibilidade)"
        return JustificationNode(
            id="AUTO_LINEAR",
            type="LINEAR_TRACE",
            description=desc,
            dependencies=[]
        )


# ============================================================
#   PARTE 2 — NOVO SISTEMA META-JUSTIFICATION COMPLETO
# ============================================================

@dataclass
class _ReflectionDecision:
    order: int
    label: str
    category: str
    justification: str
    quality: Optional[float]
    delta_quality: Optional[float]
    relations: Optional[int]
    delta_relations: Optional[int]
    context: Optional[int]


@dataclass
class _ReflectionPhase:
    name: str
    order: int
    decisions: List[_ReflectionDecision]
    enter_quality: Optional[float] = None
    exit_quality: Optional[float] = None
    delta_quality: float = 0.0
    enter_relations: Optional[int] = None
    exit_relations: Optional[int] = None
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
        if is_alert_decision(decision.label, decision.category):
            self.alert = True


# ============================================================
#  PARTE 3 — Construtores auxiliares da Meta-Reflexão nova
# ============================================================

def _decision_from_operation(entry: TraceOperation) -> _ReflectionDecision:
    category = classify_trace_category(entry.label)
    justification = decision_justification(entry.label, category)
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
    decisions = [_decision_to_node(d) for d in phase.decisions]
    fields: Dict[str, Node] = {
        "tag": entity("reflection_phase"),
        "name": entity(phase.name),
        "label": entity(phase_label(phase.name)),
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
    fields: Dict[str, Node] = {
        "tag": entity("reflection_decision"),
        "order": number(decision.order),
        "label": entity(decision.label),
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
        key=lambda p: (
            len(p.decisions),
            abs(p.delta_quality),
            p.delta_relations,
            -p.order,
        ),
    )


def _phase_chain(phases: Sequence[_ReflectionPhase]) -> str:
    if not phases:
        return ""
    labels = [phase_label(p.name) for p in phases]
    return "→".join(labels)


def _reflection_digest(decisions: Sequence[_ReflectionDecision],
                       phases: Sequence[_ReflectionPhase]) -> str:
    h = blake2b(digest_size=16)
    for d in decisions:
        h.update(f"{d.order}:{d.category}:{d.label}".encode())
        if d.delta_quality is not None:
            h.update(f"dq={d.delta_quality:.6f}".encode())
        if d.delta_relations is not None:
            h.update(f"dr={d.delta_relations}".encode())
    for p in phases:
        h.update(f"phase:{p.name}:{len(p.decisions)}".encode())
        if p.alert:
            h.update(b"alert")
    return h.hexdigest()


# ============================================================
#     PARTE 4 — FUNÇÃO PRINCIPAL: build_meta_reflection
# ============================================================

def build_meta_reflection(reasoning: Node | None) -> Node | None:
    """
    Constrói um nó LIU `meta_reflection` a partir do histórico
    de meta_reasoning (nova forma).
    """
    operations = extract_trace_operations(reasoning)
    if not operations:
        return None

    decisions = [_decision_from_operation(op) for op in operations]
    phases = _build_phases(decisions)
    digest = _reflection_digest(decisions, phases)
    dominant = _dominant_phase(phases)
    phase_nodes = [_phase_to_node(p) for p in phases]
    chain = _phase_chain(phases)
    alert_names = [p.name for p in phases if p.alert]

    fields: Dict[str, Node] = {
        "tag": entity("meta_reflection"),
        "decision_count": number(len(decisions)),
        "phase_count": number(len(phases)),
        "phase_chain": liu_text(chain),
        "digest": liu_text(digest),
        "phases": list_node(phase_nodes),
    }

    if dominant:
        fields["dominant_phase"] = entity(dominant.name)

    if alert_names:
        fields["alert_phases"] = list_node(entity(n) for n in alert_names)

    return liu_struct(**fields)


__all__ = ["build_meta_reflection", "MetaReflectionEngine", "JustificationNode"]

