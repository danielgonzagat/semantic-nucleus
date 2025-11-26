"""
Executa planos de meta-cálculo sobre a ΣVM para materializar respostas determinísticas.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict
import json

from liu import Node, to_json

from svm.vm import SigmaVM
from svm.verifier import verify_program, VerificationError

from .state import SessionCtx
from .meta_transformer import MetaCalculationPlan


@dataclass(frozen=True)
class MetaCalculationResult:
    """Resultado determinístico da execução de um MetaCalculationPlan."""

    plan: MetaCalculationPlan
    answer: Node | None
    snapshot: Dict[str, Any] | None
    error: str | None = None
    consistent: bool = True
    code_summary: Node | None = None


def execute_meta_plan(
    plan: MetaCalculationPlan,
    struct_node: Node,
    session: SessionCtx,
    code_summary: Node | None = None,
) -> MetaCalculationResult:
    """
    Carrega o plano em uma ΣVM limpa e executa o bytecode planejado.
    """

    try:
        verify_program(plan.program)
    except VerificationError as exc:
        return MetaCalculationResult(
            plan=plan,
            answer=None,
            snapshot=None,
            error=f"program_verification_failed:{exc}",
            consistent=False,
            code_summary=code_summary,
        )
    vm = SigmaVM(session=session)
    try:
        vm.load(plan.program, initial_struct=struct_node, session=session)
        answer = vm.run()
        snapshot = _serialize_snapshot(vm.snapshot(), code_summary=code_summary)
        return MetaCalculationResult(
            plan=plan,
            answer=answer,
            snapshot=snapshot,
            consistent=True,
            code_summary=code_summary,
        )
    except Exception as exc:  # determinístico: captura para auditoria
        return MetaCalculationResult(
            plan=plan,
            answer=None,
            snapshot=None,
            error=str(exc),
            consistent=False,
            code_summary=code_summary,
        )


def _serialize_snapshot(raw: Dict[str, Any], *, code_summary: Node | None = None) -> Dict[str, Any]:
    def _maybe(node: Any) -> Any:
        if isinstance(node, Node):
            return to_json(node)
        return node

    result = {
        "pc": raw.get("pc"),
        "stack_depth": raw.get("stack_depth"),
        "stack": [_maybe(item) for item in raw.get("stack", [])],
        "registers": raw.get("registers"),
        "register_values": [_maybe(item) for item in raw.get("register_values", [])],
        "call_stack": raw.get("call_stack"),
        "isr_digest": raw.get("isr_digest"),
        "answer": _maybe(raw.get("answer")),
    }
    if code_summary is not None:
        summary_json_str = to_json(code_summary)
        summary_json = json.loads(summary_json_str)
        result["code_summary"] = summary_json
        result["code_summary_functions"] = _extract_function_names(summary_json)
        details = _extract_function_details(summary_json)
        if details:
            result["code_summary_function_details"] = details
    return result


def _extract_function_names(summary_json: Dict[str, Any]) -> list[str]:
    functions = summary_json.get("fields", {}).get("functions")
    if not functions or functions.get("kind") != "LIST":
        return []
    names = []
    for entry in functions.get("args", []):
        name = entry.get("fields", {}).get("name", {}).get("label")
        if name:
            names.append(name)
    return names


def _extract_function_details(summary_json: Dict[str, Any]) -> list[dict[str, object]]:
    functions = summary_json.get("fields", {}).get("functions")
    if not functions or functions.get("kind") != "LIST":
        return []
    details: list[dict[str, object]] = []
    for entry in functions.get("args", []):
        fields = entry.get("fields", {})
        name = fields.get("name", {}).get("label")
        detail: dict[str, object] = {"name": name}
        param_count = fields.get("param_count", {}).get("value")
        if param_count is not None:
            detail["param_count"] = int(param_count)
        params_field = fields.get("parameters")
        if params_field and params_field.get("kind") == "LIST":
            detail["parameters"] = [arg.get("label", "") for arg in params_field.get("args", [])]
        details.append(detail)
    return details


__all__ = ["MetaCalculationResult", "execute_meta_plan"]
