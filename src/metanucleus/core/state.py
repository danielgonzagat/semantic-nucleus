"""
Estado determinístico do Metanúcleo.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Set, Tuple, Dict

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
