"""
Estruturas determinísticas para síntese formal (MetaPlanner/síntese de provas+planos).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Tuple

from liu import (
    Node,
    entity,
    text,
    list_node,
    struct as liu_struct,
    number,
)


@dataclass(frozen=True, slots=True)
class SynthesisStep:
    label: str
    description: str
    score: float

    def to_node(self) -> Node:
        return liu_struct(
            tag=entity("synth_step"),
            label=entity(self.label),
            description=text(self.description),
            score=number(round(self.score, 4)),
        )


@dataclass(frozen=True, slots=True)
class SynthesisPlan:
    plan_id: str
    steps: Tuple[SynthesisStep, ...]
    kind: str = "plan"

    def to_node(self) -> Node:
        return liu_struct(
            tag=entity("synth_plan_meta"),
            plan_id=text(self.plan_id),
            kind=entity(self.kind),
            step_count=number(len(self.steps)),
            steps=list_node(step.to_node() for step in self.steps),
        )


@dataclass(frozen=True, slots=True)
class ProofSynthesis:
    statement: str
    truth: str
    rationale: str

    def to_node(self) -> Node:
        return liu_struct(
            tag=entity("synth_proof_meta"),
            statement=text(self.statement),
            truth=entity(self.truth),
            rationale=text(self.rationale),
        )


__all__ = [
    "SynthesisPlan",
    "SynthesisStep",
    "ProofSynthesis",
]
