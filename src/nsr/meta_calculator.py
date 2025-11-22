"""
Executa planos de meta-cálculo sobre a ΣVM para materializar respostas determinísticas.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

from liu import Node

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
        snapshot = vm.snapshot()
        return MetaCalculationResult(plan=plan, answer=answer, snapshot=snapshot)
    except Exception as exc:  # determinístico: captura para auditoria
        return MetaCalculationResult(plan=plan, answer=None, snapshot=None, error=str(exc))


__all__ = ["MetaCalculationResult", "execute_meta_plan"]
