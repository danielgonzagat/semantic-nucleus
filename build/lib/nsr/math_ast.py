"""
Conversores determinísticos de instruções matemáticas em AST LIU auditável.
"""

from __future__ import annotations

from liu import entity, struct as liu_struct, text as liu_text, number, Node

from .math_core import MathInstruction
from .meta_structures import lc_term_to_node


def build_math_ast_node(instruction: MathInstruction, *, value: float | None = None) -> Node:
    """
    Serializa `MathInstruction` em um STRUCT `math_ast`.
    """

    term = lc_term_to_node(instruction.as_term())
    fields: dict[str, Node] = {
        "tag": entity("math_ast"),
        "language": entity(instruction.language),
        "expression": liu_text(instruction.expression),
        "operator": entity(instruction.operation.upper()),
        "term": term,
        "operand_count": number(len(instruction.operands)),
    }
    if value is not None:
        fields["value"] = number(value)
    return liu_struct(**fields)


__all__ = ["build_math_ast_node"]
