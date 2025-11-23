"""
Mapeia cálculos LC-Ω para pipelines Φ (ΣVM + NSR) de forma determinística.
"""

from __future__ import annotations

from typing import Tuple

from liu import Node, operation
from svm.opcodes import Opcode

from .lc_omega import MetaCalculation

_TEXT_PIPELINES: dict[str, Tuple[Opcode, ...]] = {
    "STATE_QUERY": (Opcode.PHI_NORMALIZE, Opcode.PHI_INFER, Opcode.PHI_SUMMARIZE),
    "STATE_ASSERT": (
        Opcode.PHI_NORMALIZE,
        Opcode.PHI_ANSWER,
        Opcode.PHI_EXPLAIN,
        Opcode.PHI_SUMMARIZE,
    ),
    "FACT_QUERY": (Opcode.PHI_NORMALIZE, Opcode.PHI_INFER, Opcode.PHI_SUMMARIZE),
    "COMMAND_ROUTE": (Opcode.PHI_NORMALIZE, Opcode.PHI_INFER, Opcode.PHI_SUMMARIZE),
    "EMIT_GREETING": (Opcode.PHI_NORMALIZE, Opcode.PHI_SUMMARIZE),
    "EMIT_THANKS": (Opcode.PHI_NORMALIZE, Opcode.PHI_SUMMARIZE),
    "EMIT_FAREWELL": (Opcode.PHI_NORMALIZE, Opcode.PHI_SUMMARIZE),
    "EMIT_CONFIRM": (Opcode.PHI_NORMALIZE, Opcode.PHI_SUMMARIZE),
}
_DEFAULT_TEXT_PIPELINE: Tuple[Opcode, ...] = (Opcode.PHI_NORMALIZE, Opcode.PHI_SUMMARIZE)

_OPCODE_TO_PHI_LABEL = {
    Opcode.PHI_NORMALIZE: "NORMALIZE",
    Opcode.PHI_INFER: "INFER",
    Opcode.PHI_ANSWER: "ANSWER",
    Opcode.PHI_EXPLAIN: "EXPLAIN",
    Opcode.PHI_SUMMARIZE: "SUMMARIZE",
}


def text_opcode_pipeline(calculus: MetaCalculation | None) -> Tuple[Opcode, ...]:
    """
    Retorna a sequência determinística de opcodes Φ para um cálculo textual.
    """

    operator = (calculus.operator if calculus else "").upper()
    return _TEXT_PIPELINES.get(operator, _DEFAULT_TEXT_PIPELINE)


def text_operation_pipeline(
    calculus: MetaCalculation | None, struct_node: Node | None = None
) -> Tuple[Node, ...]:
    """
    Converte o pipeline Φ em operações NSR (fila de operadores) preservando argumentos.
    """

    opcodes = text_opcode_pipeline(calculus)
    operations = []
    for opcode in opcodes:
        label = _OPCODE_TO_PHI_LABEL.get(opcode)
        if not label:
            continue
        if label in {"ANSWER", "EXPLAIN"} and struct_node is not None:
            operations.append(operation(label, struct_node))
        else:
            operations.append(operation(label))
    return tuple(operations)


__all__ = ["text_opcode_pipeline", "text_operation_pipeline"]
