"""
Executa planos de meta-cálculo sobre a ΣVM para materializar respostas determinísticas.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

from liu import Node, to_json

from svm.vm import SigmaVM

from .state import SessionCtx
from .meta_transformer import MetaCalculationPlan


@dataclass(frozen=True, slots=True)
class MetaCalculationResult:
    """Resultado determinístico da execução de um MetaCalculationPlan."""

    plan: MetaCalculationPlan
    answer: Node | None
    snapshot: Dict[str, Any] | None
    error: str | None = None
    consistent: bool = True


def execute_meta_plan(
    plan: MetaCalculationPlan,
    struct_node: Node,
    session: SessionCtx,
) -> MetaCalculationResult:
    """
    Carrega o plano em uma ΣVM limpa e executa o bytecode planejado.
    """

    vm = SigmaVM(session=session)
    try:
        vm.load(plan.program, initial_struct=struct_node, session=session)
        answer = vm.run()
        snapshot = _serialize_snapshot(vm.snapshot())
        return MetaCalculationResult(plan=plan, answer=answer, snapshot=snapshot, consistent=True)
    except Exception as exc:  # determinístico: captura para auditoria
        return MetaCalculationResult(
            plan=plan,
            answer=None,
            snapshot=None,
            error=str(exc),
            consistent=False,
        )


def _serialize_snapshot(raw: Dict[str, Any]) -> Dict[str, Any]:
    def _maybe(node: Any) -> Any:
        if isinstance(node, Node):
            return to_json(node)
        return node

    return {
        "pc": raw.get("pc"),
        "stack_depth": raw.get("stack_depth"),
        "stack": [_maybe(item) for item in raw.get("stack", [])],
        "registers": raw.get("registers"),
        "register_values": [_maybe(item) for item in raw.get("register_values", [])],
        "call_stack": raw.get("call_stack"),
        "isr_digest": raw.get("isr_digest"),
        "answer": _maybe(raw.get("answer")),
    }


__all__ = ["MetaCalculationResult", "execute_meta_plan"]
