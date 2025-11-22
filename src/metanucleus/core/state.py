"""
Estado determinístico do Metanúcleo.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Set

from .liu import Node, NodeKind, nil


@dataclass(slots=True)
class ISR:
    """
    Estado Semântico Reativo mínimo (inspiração NSR).
    """

    ontology: Set[Node] = field(default_factory=set)
    relations: Set[Node] = field(default_factory=set)
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


def reset_answer(state: MetaState) -> None:
    state.isr.answer = nil()
    state.isr.quality = 0.0
