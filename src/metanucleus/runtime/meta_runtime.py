"""
Orquestrador determinístico do Metanúcleo.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Tuple

from metanucleus.core.liu import Node, NodeKind, op
from metanucleus.core.state import MetaState
from .adapters import TextInputAdapter, classify_input, InputKind
from .renderer import OutputRenderer
from .scheduler import Scheduler


@dataclass(slots=True)
class MetaRuntime:
    state: MetaState
    text_adapter: TextInputAdapter = field(default_factory=TextInputAdapter)
    scheduler: Scheduler = field(default_factory=Scheduler)
    renderer: OutputRenderer = field(default_factory=OutputRenderer)

    def handle_request(self, raw_input: str, lang: str | None = None) -> str:
        kind = classify_input(raw_input)
        if kind is not InputKind.TEXT:
            return "[META] Entrada vazia."
        msg = self.text_adapter.to_liu(raw_input, lang)
        self._inject_message(msg)
        self.scheduler.run(self.state)
        self.state.metrics.total_requests += 1
        return self.renderer.render(self.state)

    def _inject_message(self, msg: Node) -> None:
        isr = self.state.isr
        isr.context.append(msg)
        # manter fila determinística: normalize → answer
        isr.ops_queue.append(op("NORMALIZE"))
        isr.ops_queue.append(op("ANSWER", msg))
