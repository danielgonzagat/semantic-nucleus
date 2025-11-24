"""
Assembler/Disassembler textual para a ΣVM.
"""

from __future__ import annotations

import shlex
from typing import Iterable, List, Sequence

from .bytecode import Instruction
from .opcodes import Opcode
from .opcode_traits import (
    CONST_OPERAND_OPS,
    REG_OPERAND_OPS,
    COUNT_OPERAND_OPS,
    TARGET_OPERAND_OPS,
    OPTIONAL_OPERAND_OPS,
    REQUIRE_OPERAND_OPS,
    MAX_REGISTER_INDEX,
)


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
    if opcode in CONST_OPERAND_OPS:
        if len(parts) != 2:
            raise ValueError(f"{opcode.name} requires constant index operand")
        return int(parts[1])
    if opcode in REG_OPERAND_OPS:
        if len(parts) != 2:
            raise ValueError(f"{opcode.name} requires register operand")
        operand = int(parts[1])
        if not 0 <= operand <= MAX_REGISTER_INDEX:
            raise ValueError("register index must be between 0 and 7")
        return operand
    if opcode in COUNT_OPERAND_OPS:
        if len(parts) != 2:
            raise ValueError(f"{opcode.name} requires count operand")
        operand = int(parts[1])
        if operand < 0:
            raise ValueError(f"{opcode.name} count operand must be non-negative")
        return operand
    if opcode in TARGET_OPERAND_OPS:
        if len(parts) != 2:
            raise ValueError(f"{opcode.name} requires target operand")
        operand = int(parts[1])
        if operand < 0:
            raise ValueError("target operand must be non-negative")
        return operand
    if opcode in OPTIONAL_OPERAND_OPS:
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
        if inst.opcode in REQUIRE_OPERAND_OPS or inst.operand:
            lines.append(f"{inst.opcode.name} {inst.operand}")
        else:
            lines.append(inst.opcode.name)
    return "\n".join(lines)


__all__ = ["assemble", "disassemble"]
