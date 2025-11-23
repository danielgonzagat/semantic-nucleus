"""
Tabulações determinísticas das instruções da ΣVM.

Estas coleções são usadas por múltiplos módulos (assembler, verificador)
para garantir que todos os opcodes recebam os operandos corretos e respeitem
as mesmas invariantes estruturais.
"""

from __future__ import annotations

from typing import Set

from .opcodes import Opcode


CONST_OPERAND_OPS: Set[Opcode] = {
    Opcode.PUSH_TEXT,
    Opcode.PUSH_CONST,
    Opcode.PUSH_KEY,
    Opcode.PUSH_NUMBER,
    Opcode.PUSH_BOOL,
}

REG_OPERAND_OPS: Set[Opcode] = {
    Opcode.LOAD_REG,
    Opcode.STORE_REG,
}

COUNT_OPERAND_OPS: Set[Opcode] = {
    Opcode.NEW_STRUCT,
    Opcode.BUILD_STRUCT,
    Opcode.BEGIN_STRUCT,
    Opcode.NEW_LIST,
    Opcode.NEW_REL,
    Opcode.NEW_OP,
}

TARGET_OPERAND_OPS: Set[Opcode] = {
    Opcode.JMP,
    Opcode.CALL,
}

OPTIONAL_OPERAND_OPS: Set[Opcode] = {Opcode.TRAP}

REQUIRE_OPERAND_OPS: Set[Opcode] = (
    CONST_OPERAND_OPS
    | REG_OPERAND_OPS
    | COUNT_OPERAND_OPS
    | TARGET_OPERAND_OPS
)

MAX_REGISTER_INDEX = 7

__all__ = [
    "CONST_OPERAND_OPS",
    "REG_OPERAND_OPS",
    "COUNT_OPERAND_OPS",
    "TARGET_OPERAND_OPS",
    "OPTIONAL_OPERAND_OPS",
    "REQUIRE_OPERAND_OPS",
    "MAX_REGISTER_INDEX",
]
