"""
Máquina virtual semântica ΣVM integrada ao ISR/NSR.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field, replace
from hashlib import blake2b
from typing import Any, List

from liu import (
    NIL,
    Node,
    NodeKind,
    boolean,
    list_node,
    normalize,
    number,
    operation,
    relation,
    struct,
    text,
)
from nsr.operators import apply_operator
from nsr.rules import unify as nsr_unify
from nsr.state import ISR, SessionCtx, initial_isr

from .assembler import assemble
from .bytecode import Instruction, decode, encode
from .opcodes import Opcode


@dataclass(slots=True)
class Program:
    instructions: List[Instruction]
    constants: List[Any] = field(default_factory=list)


class SigmaVM:
    """
    VM determinística com pilha, registradores e estado ISR embarcado.
    """

    def __init__(self, session: SessionCtx | None = None):
        self.session: SessionCtx = session or SessionCtx()
        self.program: Program | None = None
        self.stack: List[Node] = []
        self.registers: List[Node | None] = [None] * 8
        self.answer: Node | None = None
        self.pc: int = 0
        self.call_stack: List[int] = []
        self.isr: ISR | None = None

    # ---------------------------------------------------------------------
    # Lifecycle
    # ---------------------------------------------------------------------
    def load(self, program: Program, initial_struct: Node | None = None, session: SessionCtx | None = None) -> None:
        self.program = program
        if session is not None:
            self.session = session
        self.stack.clear()
        self.registers = [None] * 8
        self.answer = None
        self.pc = 0
        self.call_stack.clear()
        self.isr = initial_isr(initial_struct or struct(), self.session)

    # ---------------------------------------------------------------------
    def run(self) -> Node:
        if self.program is None:
            raise RuntimeError("program not loaded")
        instructions = self.program.instructions
        while self.pc < len(instructions):
            inst = instructions[self.pc]
            self.pc += 1
            self._execute(inst)
        return self._final_answer()

    # ------------------------------------------------------------------
    # Instruction dispatch
    # ------------------------------------------------------------------
    def _execute(self, inst: Instruction) -> None:
        opcode = inst.opcode
        if opcode in {Opcode.PUSH_TEXT, Opcode.PUSH_KEY}:
            self._push_text_operand(inst.operand)
        elif opcode is Opcode.PUSH_CONST:
            self._push_const(inst.operand)
        elif opcode is Opcode.PUSH_NUMBER:
            self._push_number(inst.operand)
        elif opcode is Opcode.PUSH_BOOL:
            self._push_bool(inst.operand)
        elif opcode is Opcode.LOAD_REG:
            self._instr_load_reg(inst.operand)
        elif opcode is Opcode.STORE_REG:
            self._instr_store_reg(inst.operand)
        elif opcode in {Opcode.NEW_STRUCT, Opcode.BUILD_STRUCT, Opcode.BEGIN_STRUCT}:
            self._instr_new_struct(inst.operand)
        elif opcode is Opcode.NEW_LIST:
            self._instr_new_list(inst.operand)
        elif opcode is Opcode.NEW_REL:
            self._instr_new_relation(inst.operand)
        elif opcode is Opcode.NEW_OP:
            self._instr_new_operation(inst.operand)
        elif opcode is Opcode.GET_FIELD:
            self._instr_get_field()
        elif opcode is Opcode.SET_FIELD:
            self._instr_set_field()
        elif opcode is Opcode.ADD_REL:
            self._instr_add_rel()
        elif opcode is Opcode.HAS_REL:
            self._instr_has_rel()
        elif opcode is Opcode.UNIFY_EQ:
            self._instr_unify_eq()
        elif opcode is Opcode.UNIFY_REL:
            self._instr_unify_rel()
        elif opcode is Opcode.ENQ_OP:
            self._instr_enqueue_op()
        elif opcode is Opcode.DISPATCH:
            self._instr_dispatch()
        elif opcode is Opcode.PHI_NORMALIZE:
            self._apply_phi("NORMALIZE")
        elif opcode is Opcode.PHI_INFER:
            self._apply_phi("INFER")
        elif opcode is Opcode.PHI_ANSWER:
            payload = self._pop() if self.stack else struct()
            self._apply_phi("ANSWER", payload)
        elif opcode is Opcode.PHI_EXPLAIN:
            focus = self._pop() if self.stack else struct()
            self._apply_phi("EXPLAIN", focus)
        elif opcode is Opcode.PHI_SUMMARIZE:
            self._apply_phi("SUMMARIZE")
        elif opcode is Opcode.JMP:
            self._instr_jmp(inst.operand)
        elif opcode is Opcode.CALL:
            self._instr_call(inst.operand)
        elif opcode is Opcode.RET:
            self._instr_ret()
        elif opcode is Opcode.HASH_STATE:
            self._instr_hash_state()
        elif opcode is Opcode.STORE_ANSWER:
            self.answer = self._pop()
        elif opcode is Opcode.NOOP:
            return
        elif opcode is Opcode.TRAP:
            self._instr_trap(inst.operand)
        elif opcode is Opcode.HALT:
            self.pc = len(self.program.instructions)
        else:
            raise ValueError(f"Unsupported opcode {opcode}")

    # ------------------------------------------------------------------
    # Instruction helpers
    # ------------------------------------------------------------------
    def _push_text_operand(self, idx: int) -> None:
        self._push(text(str(self._constant(idx))))

    def _push_const(self, idx: int) -> None:
        value = self._constant(idx)
        if isinstance(value, Node):
            self._push(value)
        elif isinstance(value, bool):
            self._push(boolean(value))
        elif isinstance(value, (int, float)):
            self._push(number(value))
        elif value is None:
            self._push(NIL)
        else:
            self._push(text(str(value)))

    def _push_number(self, idx: int) -> None:
        value = self._constant(idx)
        if not isinstance(value, (int, float)):
            raise RuntimeError("PUSH_NUMBER expects numeric constant")
        self._push(number(value))

    def _push_bool(self, idx: int) -> None:
        value = self._constant(idx)
        if isinstance(value, str):
            parsed = value.lower() in {"1", "true", "t", "yes"}
        else:
            parsed = bool(value)
        self._push(boolean(parsed))

    def _instr_load_reg(self, reg: int) -> None:
        value = self.registers[reg]
        if value is None:
            raise RuntimeError(f"register R{reg} is empty")
        self._push(value)

    def _instr_store_reg(self, reg: int) -> None:
        self.registers[reg] = self._pop()

    def _instr_new_struct(self, field_count: int) -> None:
        fields: list[tuple[str, Node]] = []
        for _ in range(field_count):
            key = self._pop_text()
            value = self._pop()
            fields.append((key, value))
        self._push(struct(**dict(reversed(fields))))

    def _instr_new_list(self, size: int) -> None:
        items = [self._pop() for _ in range(size)]
        items.reverse()
        self._push(list_node(items))

    def _instr_new_relation(self, arity: int) -> None:
        args = [self._pop() for _ in range(arity)]
        args.reverse()
        label = self._pop_text()
        self._push(relation(label, *args))

    def _instr_new_operation(self, arity: int) -> None:
        args = [self._pop() for _ in range(arity)]
        args.reverse()
        label = self._pop_text()
        self._push(operation(label, *args))

    def _instr_get_field(self) -> None:
        key = self._pop_text()
        node = self._pop()
        if node.kind is not NodeKind.STRUCT:
            raise RuntimeError("GET_FIELD expects STRUCT")
        mapping = dict(node.fields)
        self._push(mapping.get(key, NIL))

    def _instr_set_field(self) -> None:
        value = self._pop()
        key = self._pop_text()
        node = self._pop()
        if node.kind is not NodeKind.STRUCT:
            raise RuntimeError("SET_FIELD expects STRUCT")
        mapping = dict(node.fields)
        mapping[key] = value
        self._push(struct(**mapping))

    def _instr_add_rel(self) -> None:
        rel = self._pop()
        if rel.kind is not NodeKind.REL:
            raise RuntimeError("ADD_REL expects relation node")
        self._ensure_isr()
        dedup = tuple(dict.fromkeys(self.isr.relations + (normalize(rel),)))
        self.isr = replace(self.isr, relations=dedup)
        self._push(rel)

    def _instr_has_rel(self) -> None:
        rel = self._pop()
        self._ensure_isr()
        present = rel in self.isr.relations
        self._push(boolean(present))

    def _instr_unify_eq(self) -> None:
        right = self._pop()
        left = self._pop()
        self._push(boolean(left == right))

    def _instr_unify_rel(self) -> None:
        fact = self._pop()
        pattern = self._pop()
        bindings = nsr_unify(pattern, fact, {})
        if bindings is None:
            result = struct(success=boolean(False), bindings=list_node([]))
        else:
            items = [
                struct(var=text(name), value=value)
                for name, value in sorted(bindings.items())
            ]
            result = struct(success=boolean(True), bindings=list_node(items))
        self._push(result)

    def _instr_enqueue_op(self) -> None:
        op_node = self._pop()
        if op_node.kind is not NodeKind.OP:
            raise RuntimeError("ENQ_OP expects operation node")
        self._ensure_isr()
        queue = deque(self.isr.ops_queue)
        queue.append(op_node)
        self.isr = replace(self.isr, ops_queue=queue)

    def _instr_dispatch(self) -> None:
        self._ensure_isr()
        queue = deque(self.isr.ops_queue)
        if not queue:
            queue.extend([operation("ALIGN"), operation("STABILIZE"), operation("SUMMARIZE")])
        op = queue.popleft()
        self.isr = replace(self.isr, ops_queue=queue)
        self.isr = apply_operator(self.isr, op, self.session)
        if self.isr.answer.fields:
            self.answer = self.isr.answer
        self._push(op)

    def _apply_phi(self, name: str, *args: Node) -> None:
        self._ensure_isr()
        op = operation(name, *args)
        self.isr = apply_operator(self.isr, op, self.session)
        if self.isr.answer.fields:
            self.answer = self.isr.answer
            self._push(self.isr.answer)
        else:
            self._push(op)

    def _instr_jmp(self, target: int) -> None:
        self._pc_to(target)

    def _instr_call(self, target: int) -> None:
        self.call_stack.append(self.pc)
        self._pc_to(target)

    def _instr_ret(self) -> None:
        if not self.call_stack:
            raise RuntimeError("RET with empty call stack")
        self.pc = self.call_stack.pop()

    def _instr_hash_state(self) -> None:
        self._ensure_isr()
        digest = _state_signature(self.isr)
        self._push(text(digest))

    def _instr_trap(self, operand: int) -> None:
        message = "ΣVM trap"
        if operand >= 0:
            message = str(self._constant(operand))
        elif self.stack and self.stack[-1].kind is NodeKind.TEXT:
            message = self._pop().label or message
        raise RuntimeError(message)

    # ------------------------------------------------------------------
    def _pc_to(self, target: int) -> None:
        if target < 0 or target >= len(self.program.instructions):
            raise RuntimeError("jump target out of bounds")
        self.pc = target

    def _constant(self, idx: int) -> Any:
        if self.program is None:
            raise RuntimeError("program not loaded")
        try:
            return self.program.constants[idx]
        except IndexError as exc:
            raise RuntimeError(f"constant index {idx} out of range") from exc

    def _ensure_isr(self) -> None:
        if self.isr is None:
            raise RuntimeError("ISR not initialized; call load() first")

    def _pop(self) -> Node:
        if not self.stack:
            raise RuntimeError("stack underflow")
        return self.stack.pop()

    def _push(self, node: Node) -> None:
        self.stack.append(node)

    def _pop_text(self) -> str:
        node = self._pop()
        if node.kind is not NodeKind.TEXT:
            raise RuntimeError("expected TEXT atom on stack")
        return node.label or ""

    def _final_answer(self) -> Node:
        if self.answer is not None:
            return self.answer
        if self.isr and self.isr.answer.fields:
            return self.isr.answer
        raise RuntimeError("program halted without answer")

    # Snapshot utilitário
    def snapshot(self) -> dict[str, Any]:
        return {
            "pc": self.pc,
            "stack_depth": len(self.stack),
            "registers": [node.kind.value if node else None for node in self.registers],
            "isr_digest": _state_signature(self.isr) if self.isr else None,
            "answer": self.answer,
        }


def _state_signature(isr: ISR) -> str:
    answer_field = dict(isr.answer.fields).get("answer")
    answer_text = ""
    if answer_field and answer_field.label:
        answer_text = answer_field.label
    payload = f"{len(isr.relations)}|{len(isr.context)}|{len(isr.ops_queue)}|{isr.quality:.2f}|{answer_text}"
    return blake2b(payload.encode("utf-8"), digest_size=12).hexdigest()


def build_program_from_assembly(asm: str, constants: List[Any]) -> Program:
    instructions = assemble(asm)
    return Program(instructions=instructions, constants=constants)


__all__ = ["SigmaVM", "Program", "build_program_from_assembly", "encode", "decode"]
