"""
Utilidades compartilhadas para interpretar estruturas meta_reasoning.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Sequence

from liu import Node, NodeKind


@dataclass()
class TraceOperation:
    order: int
    label: str
    quality: float | None
    delta_quality: float | None
    relations: int | None
    delta_relations: int | None
    context: int | None


PHASE_LABELS = {
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


CATEGORY_JUSTIFICATION = {
    "meta_ler": "Rota inicial detectada pelo Meta-LER.",
    "meta_plan": "Plano Φ configurado para guiar o cálculo.",
    "meta_code": "Operador Φ específico para ASTs ou código.",
    "meta_memory": "Memória simbólica foi reativada ou vinculada.",
    "meta_phi": "Operador Φ executado no loop principal.",
    "meta_meta": "Operador meta-analítico aplicado ao trace.",
    "meta_guard": "Guarda estrutural detectou inconsistências.",
    "meta_halt": "Execução convergiu e produziu um halt determinístico.",
    "meta_misc": "Evento fora das categorias principais.",
}


def extract_trace_operations(reasoning: Node | None) -> List[TraceOperation]:
    """
    Converte o nó meta_reasoning em entradas ordenadas para processamento.
    """

    if reasoning is None or reasoning.kind is not NodeKind.STRUCT:
        return []
    fields = dict(reasoning.fields)
    ops_node = fields.get("operations")
    if ops_node is None or ops_node.kind is not NodeKind.LIST:
        return []
    entries: List[TraceOperation] = []
    for item in ops_node.args:
        if item.kind is not NodeKind.STRUCT:
            continue
        entry_fields = dict(item.fields)
        index_node = entry_fields.get("index")
        label_node = entry_fields.get("label")
        if index_node is None or label_node is None:
            continue
        entries.append(
            TraceOperation(
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


def classify_trace_category(label: str) -> str:
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


def decision_justification(label: str, category: str) -> str:
    base = CATEGORY_JUSTIFICATION.get(category, CATEGORY_JUSTIFICATION["meta_misc"])
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


def is_alert_decision(label: str, category: str) -> bool:
    if category == "meta_guard":
        return True
    upper = (label or "").upper()
    return upper.startswith("CONTRADICTION") or "FAILURE" in upper


def phase_label(name: str) -> str:
    return PHASE_LABELS.get(name, name)


def tree_depth(phases: Sequence[Sequence[object]]) -> int:
    """
    Calcula a profundidade teórica da árvore (raiz + fases + passos).
    """

    if not phases:
        return 1
    depth = 2  # raiz + fases
    if any(phase for phase in phases):
        depth += 1
    return depth


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


__all__ = [
    "TraceOperation",
    "extract_trace_operations",
    "classify_trace_category",
    "decision_justification",
    "is_alert_decision",
    "phase_label",
    "tree_depth",
]
