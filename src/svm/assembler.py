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
    for raw_line in source.strip().splitlines():
        line = raw_line.split(";", 1)[0].strip()
        if not line:
            continue
        parts = shlex.split(line)
        mnemonic = parts[0].upper()
        opcode = Opcode[mnemonic]
        if opcode in {Opcode.LOAD_REG, Opcode.STORE_REG}:
            if len(parts) != 2:
                raise ValueError(f"{mnemonic} requires register index operand")
            operand = int(parts[1])
            if not 0 <= operand <= 7:
                raise ValueError("register index must be between 0 and 7")
        elif opcode in {Opcode.PUSH_TEXT, Opcode.PUSH_CONST, Opcode.PUSH_KEY, Opcode.BUILD_STRUCT, Opcode.BEGIN_STRUCT}:
            if len(parts) != 2:
                raise ValueError(f"{mnemonic} requires operand")
            operand = int(parts[1])
        else:
            operand = int(parts[1]) if len(parts) > 1 else 0
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
