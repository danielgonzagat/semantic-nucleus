"""
Assembler/Disassembler textual para a ΣVM.
"""

from __future__ import annotations

import shlex
from typing import Iterable, List, Sequence, Set

from .bytecode import Instruction
from .opcodes import Opcode

_CONST_OPERANDS: Set[Opcode] = {
    Opcode.PUSH_TEXT,
    Opcode.PUSH_CONST,
    Opcode.PUSH_KEY,
    Opcode.PUSH_NUMBER,
    Opcode.PUSH_BOOL,
}
_REG_OPERANDS: Set[Opcode] = {Opcode.LOAD_REG, Opcode.STORE_REG}
_COUNT_OPERANDS: Set[Opcode] = {
    Opcode.NEW_STRUCT,
    Opcode.BUILD_STRUCT,
    Opcode.BEGIN_STRUCT,
    Opcode.NEW_LIST,
    Opcode.NEW_REL,
    Opcode.NEW_OP,
}
_TARGET_OPERANDS: Set[Opcode] = {Opcode.JMP, Opcode.CALL}
_OPTIONAL_OPERANDS: Set[Opcode] = {Opcode.TRAP}
_REQUIRE_OPERAND: Set[Opcode] = _CONST_OPERANDS | _REG_OPERANDS | _COUNT_OPERANDS | _TARGET_OPERANDS


def assemble(source: str) -> List[Instruction]:
    instructions: List[Instruction] = []
    for raw_line in source.strip().splitlines():
        line = raw_line.split(";", 1)[0].strip()
        if not line:
            continue
        parts = shlex.split(line)
        mnemonic = parts[0].strip().upper().replace("Φ", "PHI")
        opcode = Opcode[mnemonic]
        operand = _parse_operand(opcode, parts)
        instructions.append(Instruction(opcode=opcode, operand=operand))
    return instructions


def _parse_operand(opcode: Opcode, parts: Sequence[str]) -> int:
    if opcode in _CONST_OPERANDS:
        if len(parts) != 2:
            raise ValueError(f"{opcode.name} requires constant index operand")
        return int(parts[1])
    if opcode in _REG_OPERANDS:
        if len(parts) != 2:
            raise ValueError(f"{opcode.name} requires register operand")
        operand = int(parts[1])
        if not 0 <= operand <= 7:
            raise ValueError("register index must be between 0 and 7")
        return operand
    if opcode in _COUNT_OPERANDS:
        if len(parts) != 2:
            raise ValueError(f"{opcode.name} requires count operand")
        operand = int(parts[1])
        if operand < 0:
            raise ValueError(f"{opcode.name} count operand must be non-negative")
        return operand
    if opcode in _TARGET_OPERANDS:
        if len(parts) != 2:
            raise ValueError(f"{opcode.name} requires target operand")
        operand = int(parts[1])
        if operand < 0:
            raise ValueError("target operand must be non-negative")
        return operand
    if opcode in _OPTIONAL_OPERANDS:
        if len(parts) == 2:
            return int(parts[1])
        if len(parts) > 2:
            raise ValueError(f"{opcode.name} accepts at most one operand")
        return -1
    if len(parts) > 1:
        return int(parts[1])
    return 0


def disassemble(insts: Iterable[Instruction]) -> str:
    lines: List[str] = []
    for inst in insts:
        if inst.opcode in _REQUIRE_OPERAND or inst.operand:
            lines.append(f"{inst.opcode.name} {inst.operand}")
        else:
            lines.append(inst.opcode.name)
    return "\n".join(lines)


__all__ = ["assemble", "disassemble"]
