from __future__ import annotations

from liu import entity, struct as liu_struct, text as liu_text
from nsr.meta_transformer import MetaCalculationPlan, MetaRoute, _plan_digest
from svm.bytecode import Instruction
from svm.opcodes import Opcode
from svm.vm import Program


def _build_plan(
    *,
    route: MetaRoute = MetaRoute.TEXT,
    description: str = "text_phi_pipeline",
    constant_text: str = "42",
    opcodes: tuple[Opcode, ...] | None = None,
) -> MetaCalculationPlan:
    answer_node = liu_struct(tag=entity("answer"), payload=liu_text(constant_text))
    instructions = [
        Instruction(opcode, 0)
        for opcode in (opcodes or (Opcode.PUSH_CONST, Opcode.STORE_ANSWER, Opcode.HALT))
    ]
    program = Program(instructions=instructions, constants=[answer_node])
    return MetaCalculationPlan(route=route, program=program, description=description)


def test_plan_digest_matches_golden_value() -> None:
    plan = _build_plan()
    assert _plan_digest(plan) == "3d59dbf47485739b25427709207994ae"


def test_plan_digest_changes_when_instruction_order_changes() -> None:
    plan_a = _build_plan(opcodes=(Opcode.PUSH_CONST, Opcode.STORE_ANSWER, Opcode.HALT))
    plan_b = _build_plan(opcodes=(Opcode.PUSH_CONST, Opcode.HALT, Opcode.STORE_ANSWER))
    assert _plan_digest(plan_a) != _plan_digest(plan_b)


def test_plan_digest_depends_on_constant_payload() -> None:
    plan_a = _build_plan(constant_text="42")
    plan_b = _build_plan(constant_text="43")
    assert _plan_digest(plan_a) != _plan_digest(plan_b)
