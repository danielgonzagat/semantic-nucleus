"""
Estado e configuração do Núcleo Semântico Reativo (NSR).
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Deque, List, Sequence, Tuple

from liu import Node, relation, operation, struct, list_node
from ontology import core as core_ontology
from ontology import code as code_ontology


@dataclass(slots=True)
class Config:
    max_steps: int = 32
    min_quality: float = 0.6
    enable_contradiction_check: bool = False


@dataclass(slots=True)
class Rule:
    if_all: Tuple[Node, ...]
    then: Node


@dataclass(slots=True)
class Lexicon:
    synonyms: dict[str, str] = field(default_factory=dict)
    pos_hint: dict[str, str] = field(default_factory=dict)
    qualifiers: set[str] = field(default_factory=set)
    rel_words: dict[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class Token:
    lemma: str
    tag: str


DEFAULT_ONTOLOGY = core_ontology.CORE_V1 + code_ontology.CODE_V1


@dataclass(slots=True)
class SessionCtx:
    config: Config = field(default_factory=Config)
    kb_ontology: Tuple[Node, ...] = field(default_factory=lambda: DEFAULT_ONTOLOGY)
    kb_rules: Tuple[Rule, ...] = field(default_factory=tuple)
    lexicon: Lexicon = field(default_factory=Lexicon)


@dataclass(slots=True)
class ISR:
    ontology: Tuple[Node, ...]
    relations: Tuple[Node, ...]
    context: Tuple[Node, ...]
    goals: Deque[Node]
    ops_queue: Deque[Node]
    answer: Node
    quality: float

    def snapshot(self) -> "ISR":
        """Return a shallow snapshot with defensive copies of queues."""

        return ISR(
            ontology=self.ontology,
            relations=self.relations,
            context=self.context,
            goals=deque(self.goals),
            ops_queue=deque(self.ops_queue),
            answer=self.answer,
            quality=self.quality,
        )


def initial_isr(struct_node: Node, session: SessionCtx) -> ISR:
    goals = deque([operation("ANSWER", struct_node), operation("EXPLAIN", struct_node)])
    ops = deque(
        [
            operation("NORMALIZE", struct_node),
            operation("ALIGN"),
            operation("INFER"),
        ]
    )
    ctx = (struct_node,)
    return ISR(
        ontology=session.kb_ontology,
        relations=tuple(),
        context=ctx,
        goals=goals,
        ops_queue=ops,
        answer=struct(),
        quality=0.0,
    )


__all__ = [
    "Config",
    "Rule",
    "Lexicon",
    "Token",
    "SessionCtx",
    "ISR",
    "initial_isr",
]
