"""
Validador estático para programas SVMB executados pela ΣVM.

O verificador garante que operandos respeitem limites, que todos os destinos de
salto sejam válidos e que o programa finalize explicitamente com `HALT`
antes de ser enviado ao hardware simbólico.
"""

from __future__ import annotations

from typing import List

from .bytecode import Instruction
from .opcodes import Opcode
from .opcode_traits import (
    CONST_OPERAND_OPS,
    REG_OPERAND_OPS,
    COUNT_OPERAND_OPS,
    TARGET_OPERAND_OPS,
    OPTIONAL_OPERAND_OPS,
    MAX_REGISTER_INDEX,
)
from .vm import Program


class VerificationError(ValueError):
    """Erro determinístico emitido quando o bytecode viola algum contrato."""


def verify_program(program: Program, *, enforce_halt: bool = True) -> None:
    """
    Valida um `Program` antes da execução.

    Levanta `VerificationError` com uma mensagem determinística quando alguma
    invariável é quebrada.
    """

    instructions = program.instructions or []
    constants = program.constants or []
    errors: List[str] = []
    if not instructions:
        errors.append("program must contain at least one instruction")
    elif enforce_halt and instructions[-1].opcode is not Opcode.HALT:
        errors.append("last instruction must be HALT")
    const_len = len(constants)
    program_len = len(instructions)
    for idx, inst in enumerate(instructions):
        _validate_instruction(idx, inst, const_len, program_len, errors)
    if errors:
        raise VerificationError("; ".join(errors))


def _validate_instruction(
    index: int,
    inst: Instruction,
    const_len: int,
    program_len: int,
    errors: List[str],
) -> None:
    opcode = inst.opcode
    operand = inst.operand
    if opcode in CONST_OPERAND_OPS:
        if not 0 <= operand < const_len:
            errors.append(
                f"instruction {index}: {opcode.name} constant index {operand} out of range (size={const_len})"
            )
    elif opcode in REG_OPERAND_OPS:
        if not 0 <= operand <= MAX_REGISTER_INDEX:
            errors.append(
                f"instruction {index}: {opcode.name} register index {operand} out of range (0-{MAX_REGISTER_INDEX})"
            )
    elif opcode in COUNT_OPERAND_OPS:
        if operand < 0:
            errors.append(f"instruction {index}: {opcode.name} count operand must be non-negative")
    elif opcode in TARGET_OPERAND_OPS:
        if not 0 <= operand < program_len:
            errors.append(
                f"instruction {index}: {opcode.name} target {operand} out of range (0-{program_len - 1})"
            )
    elif opcode is Opcode.TRAP:
        if operand < -1:
            errors.append(f"instruction {index}: TRAP operand must be -1 or a constant index")
        elif operand >= 0 and operand >= const_len:
            errors.append(f"instruction {index}: TRAP constant index {operand} out of range (size={const_len})")
    elif opcode is Opcode.HALT and operand != 0:
        errors.append(f"instruction {index}: HALT must use operand 0")
    elif opcode not in OPTIONAL_OPERAND_OPS and opcode not in CONST_OPERAND_OPS:
        # Para instruções sem operando, garantimos que o valor padrão não é negativo.
        if operand < 0:
            errors.append(f"instruction {index}: {opcode.name} does not accept negative operands")


__all__ = ["verify_program", "VerificationError"]
