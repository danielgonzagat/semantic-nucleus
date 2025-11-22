"""
Orquestrador determinístico do Metanúcleo.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Tuple

from metanucleus.core.liu import Node, NodeKind, op
from metanucleus.core.state import MetaState, register_utterance_relation
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
        if kind is InputKind.UNKNOWN:
            return "[META] Entrada vazia."
        if kind is InputKind.CONTROL:
            result = self._handle_control(raw_input.strip())
            self.state.metrics.total_requests += 1
            return result
        msg = self.text_adapter.to_liu(raw_input, lang)
        self._inject_message(msg)
        self.scheduler.run(self.state)
        self.state.metrics.total_requests += 1
        return self.renderer.render(self.state)

    def _inject_message(self, msg: Node) -> None:
        isr = self.state.isr
        isr.context.append(msg)
        register_utterance_relation(self.state, msg)
        # manter fila determinística: normalize → answer
        isr.ops_queue.append(op("NORMALIZE"))
        isr.ops_queue.append(op("INTENT", msg))
        isr.ops_queue.append(op("ANSWER", msg))

    def _handle_control(self, command: str) -> str:
        if command == "/facts":
            relations = sorted(
                f"{name}{args}" for name, args in self.state.isr.relations
            )
            if not relations:
                return "[META] Nenhum fato registrado."
            return "[META] Fatos: " + "; ".join(relations)
        if command == "/state":
            return self._format_state()
        return f"[META] Comando desconhecido: {command}"

    def _format_state(self) -> str:
        isr = self.state.isr
        ctx_preview = [
            _preview(node) for node in isr.context[-3:]
        ]
        answer_text = _preview(isr.answer)
        return (
            "[META] Estado:"
            f" quality={isr.quality:.2f}; "
            f"context={ctx_preview}; "
            f"answer={answer_text}"
        )


def _preview(node: Node | None) -> str:
    if node is None:
        return ""
    if node.kind is NodeKind.STRUCT:
        content = node.fields.get("content") or node.fields.get("raw")
        if content and content.kind is NodeKind.TEXT and content.label:
            return content.label[:40]
    if node.kind is NodeKind.TEXT and node.label:
        return node.label[:40]
    if node.label:
        return node.label[:40]
    return node.kind.name.lower()
