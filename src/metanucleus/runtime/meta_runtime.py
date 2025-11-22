"""
Orquestrador determinístico do Metanúcleo.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Tuple

from metanucleus.core.evolution import MetaEvolution
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
        if command.startswith("/codeplan"):
            return self._format_code_plan()
        if command.startswith("/testcore"):
            return self._handle_testcore_command(command)
        if command.startswith("/evolve"):
            return self._handle_evolve_command(command)
        if command.startswith("/evolutions"):
            return self._handle_evolutions_command(command)
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

    def _format_code_plan(self) -> str:
        code_node = next(
            (
                node
                for node in reversed(self.state.isr.context)
                if node.kind is NodeKind.STRUCT
                and node.fields.get("kind")
                and node.fields["kind"].kind is NodeKind.TEXT
                and node.fields["kind"].label == "code_snippet"
            ),
            None,
        )
        if code_node is None:
            return "[CODEPLAN] Nenhum code_snippet recente."

        from metanucleus.core.ast_bridge import liu_to_python_code

        structure = code_node.fields.get("structure") or code_node.fields.get("ast")
        summary_lines = [f"[CODEPLAN] lang={_safe_label(code_node.fields.get('code_lang'))}"]
        if structure:
            summary_lines.append("AST summary:")
            summary_lines.append(liu_to_python_code(structure))
        else:
            summary_lines.append("Sem AST disponível.")
        return "\n".join(summary_lines)

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

    def _handle_evolve_command(self, command: str) -> str:
        """
        Executa o pipeline de meta-evolução para um alvo em disco.
        Uso: /evolve caminho/arquivo.py:funcao [suite=nome|suite=none]
        """
        tokens = command.split()
        if len(tokens) < 2:
            return "[META-EVOLVE] Uso: /evolve caminho/arquivo.py:funcao [suite=nome]"

        target_spec = tokens[1].strip()
        if ":" not in target_spec:
            return "[META-EVOLVE] Formato inválido. Use caminho/arquivo.py:funcao"

        path_str, func_name = target_spec.split(":", 1)
        if not func_name:
            return "[META-EVOLVE] Nome da função ausente."

        suite_name: str | None = None
        for token in tokens[2:]:
            if token.startswith("suite="):
                value = token.split("=", 1)[1].lower()
                if value in {"none", "skip", "off"}:
                    suite_name = None
                else:
                    suite_name = value

        path = Path(path_str).expanduser()
        if not path.is_absolute():
            path = Path.cwd() / path

        if not path.exists():
            return f"[META-EVOLVE] Arquivo não encontrado: {path}"

        try:
            result = MetaEvolution().evolve_file(path, func_name)
        except Exception as exc:  # pragma: no cover - proteção adicional
            return f"[META-EVOLVE] Erro durante evolução: {exc}"

        if not result.success:
            return f"[META-EVOLVE] Nenhuma otimização aplicada ({result.reason})."

        test_report_lines: list[str] = []
        test_status = "skipped"
        if suite_name is not None:
            suite = get_suite(suite_name)
            if suite is None:
                available = ", ".join(list_suites())
                return f"[META-EVOLVE] Suite desconhecida '{suite_name}'. Disponíveis: {available}"
            # executa testes em snapshot determinístico novo para garantir isolamento
            sandbox = MetaSandbox.from_state(MetaState())
            temp_runtime = sandbox.spawn_runtime()
            results = run_test_suite(temp_runtime, suite)
            passed = all(r.passed for r in results)
            status_text = "PASS" if passed else "FAIL"
            test_status = "pass" if passed else "fail"
            successes = sum(1 for r in results if r.passed)
            test_report_lines.append(
                f"  tests ({suite_name}): {status_text} ({successes}/{len(results)})"
            )
            if not passed:
                for res in results:
                    if res.passed:
                        continue
                    diff_summary = "; ".join(
                        f"{d.path} expected={d.expected} actual={d.actual}"
                        for d in res.field_diffs
                    ) or "sem detalhes"
                    test_report_lines.append(
                        f"    - {res.case.name}: {diff_summary}"
                    )
                test_report_lines.append(
                    "  Resultado dos testes incompatível. Patch não será gerado automaticamente."
                )
                self._register_evolution_event(
                    target=f"{path}:{func_name}",
                    status="tests_failed",
                    suite=suite_name,
                    patch_path=None,
                    test_status=test_status,
                    reason="testcore_failure",
                )
                return "\n".join(
                    ["[META-EVOLVE] Evolução rejeitada pelos testes."] + test_report_lines
                )

        patch_path = path.with_suffix(path.suffix + ".meta.patch")
        diff_text = result.diff or ""
        patch_path.write_text(diff_text, encoding="utf-8")

        analysis = result.analysis
        summary_lines = [
            "[META-EVOLVE] Evolução bem-sucedida.",
            f"  alvo: {path}:{func_name}",
            f"  patch: {patch_path}",
        ]
        if analysis:
            summary_lines.append(
                f"  custo: {analysis.cost_before} → {analysis.cost_after}"
            )
        if test_report_lines:
            summary_lines.extend(test_report_lines)
        else:
            summary_lines.append("  tests: skipped (use suite=nome para executar)")
        summary_lines.append("  diff preview:")
        preview = "\n".join(diff_text.splitlines()[:10]) or "(diff vazio)"
        summary_lines.append(preview)
        summary_lines.append(
            "Revise o patch gerado manualmente antes de aplicar ao repositório."
        )
        self._register_evolution_event(
            target=f"{path}:{func_name}",
            status="success",
            suite=suite_name or "skipped",
            patch_path=str(patch_path),
            test_status=test_status,
            reason="optimization_found",
        )
        return "\n".join(summary_lines)

    def _register_evolution_event(
        self,
        *,
        target: str,
        status: str,
        suite: str | None,
        patch_path: str | None,
        test_status: str,
        reason: str,
    ) -> None:
        event = {
            "target": target,
            "status": status,
            "suite": suite or "skipped",
            "patch": patch_path or "",
            "tests": test_status,
            "reason": reason,
        }
        self.state.evolution_log.append(event)
        limit = 20
        if len(self.state.evolution_log) > limit:
            del self.state.evolution_log[:-limit]

    def _handle_evolutions_command(self, command: str) -> str:
        parts = command.split()
        limit = 5
        if len(parts) == 2 and parts[1].isdigit():
            limit = max(1, min(20, int(parts[1])))
        log = self.state.evolution_log[-limit:]
        if not log:
            return "[META-EVOLVE] Nenhum evento registrado."
        lines = ["[META-EVOLVE] Últimos eventos:"]
        for entry in reversed(log):
            lines.append(
                f"  target={entry['target']} status={entry['status']} "
                f"suite={entry['suite']} tests={entry['tests']} patch={entry['patch'] or '-'}"
            )
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


def _safe_label(node: Node | None) -> str:
    if node and node.kind is NodeKind.TEXT and node.label:
        return node.label
    return ""
