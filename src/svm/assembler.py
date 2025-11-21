"""
Assembler/Disassembler textual para a ΣVM.
"""

from __future__ import annotations

import shlex
from typing import List

from .bytecode import Instruction
from .opcodes import Opcode


def assemble(source: str) -> List[Instruction]:
    instructions: List[Instruction] = []
    for line in source.strip().splitlines():
        line = line.strip()
        if not line or line.startswith(";"):
            continue
        parts = shlex.split(line)
        mnemonic = parts[0].upper()
        operand = int(parts[1]) if len(parts) > 1 else 0
        opcode = Opcode[mnemonic]
        instructions.append(Instruction(opcode=opcode, operand=operand))
    return instructions


def disassemble(insts: List[Instruction]) -> str:
    lines = []
    for inst in insts:
        if inst.operand:
            lines.append(f"{inst.opcode.name} {inst.operand}")
        else:
            lines.append(inst.opcode.name)
    return "\n".join(lines)


__all__ = ["assemble", "disassemble"]
