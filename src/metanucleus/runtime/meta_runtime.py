"""
Orquestrador determinístico do Metanúcleo.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import json
from typing import Tuple

from metanucleus.core.liu import Node, NodeKind, op
from metanucleus.core.state import MetaState, register_utterance_relation
from metanucleus.core.sandbox import MetaSandbox
from metanucleus.test.testcore import run_test_suite
from .adapters import TextInputAdapter, CodeInputAdapter, classify_input, InputKind
from .renderer import OutputRenderer
from .scheduler import Scheduler
from .test_suites import get_suite, list_suites


@dataclass(slots=True)
class MetaRuntime:
    state: MetaState
    text_adapter: TextInputAdapter = field(default_factory=TextInputAdapter)
    code_adapter: CodeInputAdapter = field(default_factory=CodeInputAdapter)
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
        if kind is InputKind.CODE:
            msg = self.code_adapter.to_liu(raw_input)
        else:
            msg = self.text_adapter.to_liu(raw_input, lang)
        self._inject_message(msg)
        self.scheduler.run(self.state)
        output = self.renderer.render(self.state)
        self._record_meta_summary(msg, output)
        self.state.metrics.total_requests += 1
        return output

    def _inject_message(self, msg: Node) -> None:
        isr = self.state.isr
        isr.context.append(msg)
        register_utterance_relation(self.state, msg)
        # manter fila determinística: normalize → answer
        isr.ops_queue.append(op("NORMALIZE"))
        isr.ops_queue.append(op("INTENT", msg))

    def _handle_control(self, command: str) -> str:
        if command.startswith("/facts"):
            relations = self.state.isr.relations
            parts = command.split()
            filters = [token.upper() for token in parts[1:]]
            if filters:
                for tag in filters:
                    relations = {rel for rel in relations if rel[0].upper() == tag}
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
        if command.startswith("/meta"):
            parts = command.split()
            limit = 1
            if len(parts) == 2 and parts[1].isdigit():
                limit = max(1, min(10, int(parts[1])))
            return self._format_meta(limit)
        if command.startswith("/testcore"):
            return self._handle_testcore_command(command)
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

    def _format_meta(self, limit: int) -> str:
        if not self.state.meta_history:
            return "[META] Nenhum meta registrado."
        entries = self.state.meta_history[-limit:]
        lines = [
            f"route={entry.get('route','')}; lang={entry.get('lang','')}; input={entry.get('input','')}; answer={entry.get('answer','')}"
            for entry in entries
        ]
        return "[META] MetaSummary:\n" + "\n".join(lines)

    def _record_meta_summary(self, msg: Node, output: str) -> None:
        if msg.kind is not NodeKind.STRUCT:
            return
        lang_node = msg.fields.get("lang")
        content_node = msg.fields.get("content") or msg.fields.get("raw")
        kind_field = msg.fields.get("kind")
        kind_label = kind_field.label if kind_field and kind_field.kind is NodeKind.TEXT else ""
        if kind_label == "utterance" or not kind_label:
            route_value = "text"
        elif kind_label == "code_snippet":
            route_value = "code"
        else:
            route_value = kind_label
        summary = {
            "route": route_value,
            "lang": (lang_node.label if lang_node and lang_node.kind is NodeKind.TEXT else ""),
            "input": (
                content_node.label if content_node and content_node.kind is NodeKind.TEXT else ""
            ),
            "answer": output,
        }
        self.state.meta_history.append(summary)
        limit = 10
        if len(self.state.meta_history) > limit:
            del self.state.meta_history[:-limit]

    def _handle_testcore_command(self, command: str) -> str:
        tokens = command.split()
        suite_name = "basic"
        json_mode = False
        for token in tokens[1:]:
            lower = token.lower()
            if lower == "json":
                json_mode = True
            elif get_suite(lower):
                suite_name = lower
            else:
                return (
                    "[TESTCORE] argumentos inválidos. "
                    f"Use um dos suites: {', '.join(list_suites())} "
                    "e opcionalmente 'json'."
                )
        return self._run_builtin_testcore(suite_name=suite_name, as_json=json_mode)

    def _run_builtin_testcore(self, suite_name: str = "basic", as_json: bool = False) -> str:
        suite = get_suite(suite_name)
        if suite is None:
            return f"[TESTCORE] suite desconhecida: {suite_name}"
        sandbox = MetaSandbox.from_state(self.state)
        temp_runtime = sandbox.spawn_runtime()
        results = run_test_suite(temp_runtime, suite)
        total = len(results)
        passed = sum(1 for r in results if r.passed)
        if as_json:
            payload = {
                "total": total,
                "passed": passed,
                "failed": total - passed,
                "results": [
                    {
                        "name": r.case.name,
                        "status": "OK" if r.passed else "FAIL",
                        "detected_intent": r.detected_intent,
                        "detected_lang": r.detected_lang,
                        "answer": r.raw_answer,
                        "patch": r.patch.module if r.patch else None,
                    }
                    for r in results
                ],
            }
            return json.dumps(payload, ensure_ascii=False)

        lines = [
            f"[TESTCORE:{suite_name}] total={total} passed={passed} failed={total - passed}"
        ]
        for result in results:
            status = "OK" if result.passed else "FAIL"
            line = (
                f"{status} {result.case.name}: "
                f"intent={result.detected_intent or '-'} "
                f"lang={result.detected_lang or '-'} "
                f"answer={result.raw_answer}"
            )
            if result.patch:
                line += f" | suggestion={result.patch.module}"
            lines.append(line)
        return "\n".join(lines)


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
