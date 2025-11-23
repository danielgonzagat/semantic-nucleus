"""
Estado e configuração do Núcleo Semântico Reativo (NSR).
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Deque, List, Mapping, Sequence, Tuple, TYPE_CHECKING

from liu import Node, NodeKind, operation, struct
from ontology import core as core_ontology
from ontology import code as code_ontology

if TYPE_CHECKING:
    from .logic_engine import LogicEngine
    from .equation import EquationSnapshotStats


@dataclass(slots=True)
class Config:
    max_steps: int = 32
    min_quality: float = 0.6
    enable_contradiction_check: bool = True
    meta_history_limit: int = 64
    calc_mode: str = "hybrid"
    memory_store_path: str | None = ".nsr_memory/memory.jsonl"
    memory_persist_limit: int = 256
    episodes_path: str | None = ".nsr_memory/episodes.jsonl"
    induction_rules_path: str | None = ".nsr_memory/rule_suggestions.jsonl"
    induction_episode_limit: int = 128
    induction_min_support: int = 3


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

    def merge(self, other: "Lexicon") -> "Lexicon":
        return Lexicon(
            synonyms={**self.synonyms, **other.synonyms},
            pos_hint={**self.pos_hint, **other.pos_hint},
            qualifiers=set(self.qualifiers) | set(other.qualifiers),
            rel_words={**self.rel_words, **other.rel_words},
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "synonyms": dict(self.synonyms),
            "pos_hint": dict(self.pos_hint),
            "qualifiers": sorted(self.qualifiers),
            "rel_words": dict(self.rel_words),
        }

    @classmethod
    def from_mapping(cls, data: Mapping[str, object]) -> "Lexicon":
        def _as_dict(key: str) -> dict[str, str]:
            raw = data.get(key, {})
            return dict(raw) if isinstance(raw, Mapping) else {}

        def _as_set(key: str) -> set[str]:
            raw = data.get(key, [])
            if isinstance(raw, Mapping):
                return set(raw.keys())
            if isinstance(raw, (list, tuple, set)):
                return {str(item) for item in raw}
            return set()

        return cls(
            synonyms=_as_dict("synonyms"),
            pos_hint=_as_dict("pos_hint"),
            qualifiers=_as_set("qualifiers"),
            rel_words=_as_dict("rel_words"),
        )


@dataclass(slots=True)
class Token:
    lemma: str
    tag: str
    payload: str | None = None
    surface: str | None = None


DEFAULT_ONTOLOGY = core_ontology.CORE_V1 + code_ontology.CODE_V1


@dataclass(slots=True)
class SessionCtx:
    config: Config = field(default_factory=Config)
    kb_ontology: Tuple[Node, ...] = field(default_factory=lambda: DEFAULT_ONTOLOGY)
    kb_rules: Tuple[Rule, ...] = field(default_factory=tuple)
    lexicon: Lexicon = field(default_factory=Lexicon)
    language_hint: str | None = None
    logic_engine: "LogicEngine | None" = None
    logic_serialized: str | None = None
    meta_history: List[Tuple[Node, ...]] = field(default_factory=list)
    meta_buffer: Tuple[Node, ...] = field(default_factory=tuple)
    memory_loaded: bool = False
    last_equation_stats: "EquationSnapshotStats | None" = None


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
    base_relations = _relations_from_struct(struct_node)
    return ISR(
        ontology=session.kb_ontology,
        relations=base_relations,
        context=ctx,
        goals=goals,
        ops_queue=ops,
        answer=struct(),
        quality=0.0,
    )


def _relations_from_struct(struct_node: Node) -> Tuple[Node, ...]:
    relations_field = dict(struct_node.fields).get("relations")
    if not relations_field or relations_field.kind is not NodeKind.LIST:
        return tuple()
    return tuple(node for node in relations_field.args if node.kind is NodeKind.REL)


__all__ = [
    "Config",
    "Rule",
    "Lexicon",
    "Token",
    "SessionCtx",
    "ISR",
    "initial_isr",
]
