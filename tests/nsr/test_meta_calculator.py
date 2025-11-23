from liu import struct

from nsr.meta_calculator import execute_meta_plan
from nsr.meta_transformer import MetaCalculationPlan, MetaRoute
from nsr.state import SessionCtx
from svm.bytecode import Instruction
from svm.opcodes import Opcode
from svm.vm import Program


def test_execute_meta_plan_returns_error_when_verification_fails():
    program = Program(
        instructions=[
            Instruction(Opcode.PUSH_CONST, 0),
            Instruction(Opcode.STORE_ANSWER, 0),
        ],  # Falta HALT
        constants=[struct(answer=struct())],
    )
    plan = MetaCalculationPlan(route=MetaRoute.TEXT, program=program, description="invalid_plan")
    session = SessionCtx()
    result = execute_meta_plan(plan, struct(), session)
    assert result.consistent is False
    assert result.answer is None
    assert result.snapshot is None
    assert result.error and "HALT" in result.error
