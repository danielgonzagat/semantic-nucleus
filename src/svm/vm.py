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
        self.registers: List[Node | None] = [None] * 8

    def load(self, program: Program) -> None:
        self.program = program
        self.stack.clear()
        self.answer = None
        self.pc = 0
        self.registers = [None] * 8

    def run(self) -> Node:
        if self.program is None:
            raise RuntimeError("program not loaded")
        instructions = self.program.instructions
        consts = self.program.constants
        while self.pc < len(instructions):
            inst = instructions[self.pc]
            self.pc += 1
            if inst.opcode is Opcode.PUSH_TEXT:
                self._push(text(consts[inst.operand]))
            elif inst.opcode is Opcode.PUSH_CONST:
                self._push(text(consts[inst.operand]))
            elif inst.opcode is Opcode.PUSH_KEY:
                self._push(text(consts[inst.operand]))
            elif inst.opcode in {Opcode.BUILD_STRUCT, Opcode.BEGIN_STRUCT}:
                fields = []
                count = inst.operand
                for _ in range(count):
                    key_label = self._pop_text()
                    value = self._pop()
                    fields.append((key_label, value))
                constructed = struct(**{k: v for k, v in fields})
                self._push(constructed)
            elif inst.opcode is Opcode.LOAD_REG:
                reg_value = self.registers[inst.operand]
                if reg_value is None:
                    raise RuntimeError(f"register R{inst.operand} is empty")
                self._push(reg_value)
            elif inst.opcode is Opcode.STORE_REG:
                self.registers[inst.operand] = self._pop()
            elif inst.opcode is Opcode.NOOP:
                continue
            elif inst.opcode is Opcode.STORE_ANSWER:
                self.answer = self._pop()
            elif inst.opcode is Opcode.HALT:
                break
            else:
                raise ValueError(f"Unsupported opcode {inst.opcode}")
        if self.answer is None:
            raise RuntimeError("program halted without answer")
        return self.answer

    def _pop(self) -> Node:
        if not self.stack:
            raise RuntimeError("stack underflow")
        return self.stack.pop()

    def _push(self, node: Node) -> None:
        self.stack.append(node)

    def _pop_text(self) -> str:
        node = self._pop()
        if node.kind is not NodeKind.TEXT:
            raise RuntimeError("STRUCT keys must be TEXT nodes")
        return node.label or ""


def build_program_from_assembly(asm: str, constants: List[str]) -> Program:
    instructions = assemble(asm)
    return Program(instructions=instructions, constants=constants)


__all__ = ["SigmaVM", "Program", "build_program_from_assembly", "encode", "decode"]
