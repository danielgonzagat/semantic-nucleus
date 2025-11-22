"""
Agendador do Metanúcleo — executa o laço Φ determinístico.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from metanucleus.core.liu import Node, NodeKind
from metanucleus.core.state import MetaState
from metanucleus.core.phi import apply_phi as default_apply_phi


@dataclass(slots=True)
class Scheduler:
    max_steps: int = 16
    apply_phi: Callable[[MetaState, Node], None] = field(default=default_apply_phi)

    def run(self, state: MetaState) -> None:
        isr = state.isr
        steps = 0
        while steps < self.max_steps and isr.ops_queue:
            steps += 1
            operator = isr.ops_queue.pop(0)
            self.apply_phi(state, operator)
            state.metrics.total_cycles += 1
            if isr.answer.kind is not NodeKind.NIL:
                break
