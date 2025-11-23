"""
Estado determinístico do Metanúcleo.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from time import time
from typing import List, Set, Tuple, Dict
from uuid import uuid4

from .liu import Node, NodeKind, nil, rel, text, entity


@dataclass(slots=True)
class ISR:
    """
    Estado Semântico Reativo mínimo (inspiração NSR).
    """

    ontology: Set[Node] = field(default_factory=set)
    relations: Set[Tuple[str, Tuple[str, ...]]] = field(default_factory=set)
    context: List[Node] = field(default_factory=list)
    goals: List[Node] = field(default_factory=list)
    ops_queue: List[Node] = field(default_factory=list)
    answer: Node = field(default_factory=nil)
    quality: float = 0.0


@dataclass(slots=True)
class Metrics:
    total_cycles: int = 0
    total_requests: int = 0
    semantic_events: int = 0
    semantic_cost_sum: float = 0.0
    semantic_cost_max: float = 0.0
    semantic_kind_counts: Dict[str, int] = field(default_factory=dict)
    intent_counts: Dict[str, int] = field(default_factory=dict)
    lang_counts: Dict[str, int] = field(default_factory=dict)


@dataclass(slots=True)
class Config:
    max_reasoning_steps: int = 32


@dataclass(slots=True)
class MetaState:
    """
    Estado global do Metanúcleo.
    """

    isr: ISR = field(default_factory=ISR)
    metrics: Metrics = field(default_factory=Metrics)
    config: Config = field(default_factory=Config)
    meta_history: List[Dict[str, str]] = field(default_factory=list)
    evolution_log: List[Dict[str, str]] = field(default_factory=list)
    id: str = field(default_factory=lambda: str(uuid4()))
    created_at: float = field(default_factory=time)
    last_updated_at: float = field(default_factory=time)

    def touch(self) -> None:
        self.last_updated_at = time()


def reset_answer(state: MetaState) -> None:
    state.isr.answer = nil()
    state.isr.quality = 0.0


def register_utterance_relation(state: MetaState, msg: Node) -> None:
    """
    Registra um fato SAID(user, utterance_preview) no conjunto de relações.
    """

    preview = ""
    if msg.kind is NodeKind.STRUCT:
        content = msg.fields.get("content") or msg.fields.get("raw")
        if content and content.kind is NodeKind.TEXT and content.label:
            preview = content.label
    if not preview and msg.label:
        preview = msg.label
    if not preview:
        preview = msg.kind.name.lower()
    relation = rel("SAID", entity("user"), text(preview))
    state.isr.relations.add(_rel_signature(relation))


def register_semantic_metrics(
    state: MetaState,
    *,
    semantic_kind: str,
    semantic_cost: float,
    intent: str,
    lang: str,
) -> None:
    metrics = state.metrics
    metrics.semantic_events += 1
    metrics.semantic_cost_sum += float(semantic_cost)
    metrics.semantic_cost_max = max(metrics.semantic_cost_max, float(semantic_cost))

    if semantic_kind:
        metrics.semantic_kind_counts[semantic_kind] = (
            metrics.semantic_kind_counts.get(semantic_kind, 0) + 1
        )
    if intent:
        metrics.intent_counts[intent] = metrics.intent_counts.get(intent, 0) + 1
    if lang:
        metrics.lang_counts[lang] = metrics.lang_counts.get(lang, 0) + 1


def _rel_signature(rel_node: Node) -> Tuple[str, Tuple[str, ...]]:
    labels = []
    for arg in rel_node.args:
        if arg.kind is NodeKind.TEXT and arg.label:
            labels.append(arg.label)
        elif arg.kind is NodeKind.NUMBER and arg.value_num is not None:
            labels.append(str(arg.value_num))
        elif arg.label:
            labels.append(arg.label)
        else:
            labels.append(arg.kind.name.lower())
    return rel_node.label or "REL", tuple(labels)
