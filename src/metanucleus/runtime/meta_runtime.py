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
        if command.startswith("/facts"):
            relations = self.state.isr.relations
            parts = command.split(maxsplit=1)
            if len(parts) == 2:
                filter_tag = parts[1].upper()
                relations = {rel for rel in relations if rel[0].upper() == filter_tag}
            relations_sorted = sorted(f"{name}{args}" for name, args in relations)
            if not relations_sorted:
                return "[META] Nenhum fato registrado."
            return "[META] Fatos: " + "; ".join(relations_sorted)
        if command == "/state":
            return self._format_state()
        if command == "/context":
            return self._format_context()
        if command == "/reset":
            self.state.isr.context.clear()
            self.state.isr.goals.clear()
            self.state.isr.ops_queue.clear()
            self.state.isr.answer = Node(kind=NodeKind.NIL)
            self.state.isr.quality = 0.0
            return "[META] Estado reativo resetado."
        if command == "/goals":
            goals = [g.label or g.kind.name for g in self.state.isr.ops_queue[:5]]
            return "[META] Goals/Ops: " + ", ".join(goals or ["(vazio)"])
        return f"[META] Comando desconhecido: {command}"

    def _format_state(self) -> str:
        isr = self.state.isr
        ctx_preview = _context_snippets(isr.context, limit=3)
        answer_text = _preview(isr.answer)
        return (
            "[META] Estado:"
            f" quality={isr.quality:.2f}; "
            f"context={ctx_preview}; "
            f"answer={answer_text}"
        )

    def _format_context(self) -> str:
        snippets = _context_snippets(self.state.isr.context, limit=5)
        if not snippets:
            return "[META] Contexto vazio."
        return "[META] Contexto: " + " | ".join(snippets)


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


def _context_snippets(context: list[Node], limit: int) -> list[str]:
    return [_preview(node) for node in context[-limit:] if node]
