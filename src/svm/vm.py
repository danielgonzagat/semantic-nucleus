"""
Máquina virtual semântica ΣVM simplificada.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from liu import Node, NodeKind, struct, text

from .assembler import assemble
from .bytecode import Instruction, encode, decode
from .opcodes import Opcode


@dataclass
class Program:
    instructions: List[Instruction]
    constants: List[str] = field(default_factory=list)


class SigmaVM:
    def __init__(self):
        self.program: Program | None = None
        self.stack: List[Node] = []
        self.answer: Node | None = None
        self.pc: int = 0

    def load(self, program: Program) -> None:
        self.program = program
        self.stack.clear()
        self.answer = None
        self.pc = 0

    def run(self) -> Node:
        if self.program is None:
            raise RuntimeError("program not loaded")
        instructions = self.program.instructions
        consts = self.program.constants
        while self.pc < len(instructions):
            inst = instructions[self.pc]
            self.pc += 1
            if inst.opcode is Opcode.PUSH_TEXT:
                literal = consts[inst.operand]
                self.stack.append(text(literal))
            elif inst.opcode is Opcode.BUILD_STRUCT:
                fields = []
                for _ in range(inst.operand):
                    value = self.stack.pop()
                    key_node = self.stack.pop()
                    if key_node.kind is not NodeKind.TEXT:
                        raise ValueError("STRUCT keys must be TEXT nodes")
                    fields.append((key_node.label or "", value))
                constructed = struct(**{k: v for k, v in fields})
                self.stack.append(constructed)
            elif inst.opcode is Opcode.STORE_ANSWER:
                self.answer = self.stack.pop()
            elif inst.opcode is Opcode.HALT:
                break
            else:
                raise ValueError(f"Unsupported opcode {inst.opcode}")
        if self.answer is None:
            raise RuntimeError("program halted without answer")
        return self.answer


def build_program_from_assembly(asm: str, constants: List[str]) -> Program:
    instructions = assemble(asm)
    return Program(instructions=instructions, constants=constants)


__all__ = ["SigmaVM", "Program", "build_program_from_assembly", "encode", "decode"]
