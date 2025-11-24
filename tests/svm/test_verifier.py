from liu import struct

from svm import Program, verify_program, VerificationError
from svm.bytecode import Instruction
from svm.opcodes import Opcode


def _plan(*instructions, constants=None):
    return Program(instructions=list(instructions), constants=constants or [])


def test_verify_program_accepts_valid_program():
    program = _plan(
        Instruction(Opcode.PUSH_CONST, 0),
        Instruction(Opcode.STORE_ANSWER, 0),
        Instruction(Opcode.HALT, 0),
        constants=[struct(answer=struct())],
    )
    verify_program(program)  # não deve levantar


def test_verify_program_requires_halt():
    program = _plan(Instruction(Opcode.NOOP, 0))
    try:
        verify_program(program)
    except VerificationError as exc:
        assert "HALT" in str(exc)
    else:
        raise AssertionError("VerificationError esperado")


def test_verify_program_checks_constant_bounds():
    program = _plan(
        Instruction(Opcode.PUSH_CONST, 1),
        Instruction(Opcode.STORE_ANSWER, 0),
        Instruction(Opcode.HALT, 0),
        constants=[42],
    )
    try:
        verify_program(program)
    except VerificationError as exc:
        assert "constant index" in str(exc)
    else:
        raise AssertionError("VerificationError esperado")


def test_verify_program_checks_register_bounds():
    program = _plan(
        Instruction(Opcode.LOAD_REG, 8),
        Instruction(Opcode.HALT, 0),
    )
    try:
        verify_program(program)
    except VerificationError as exc:
        assert "register index" in str(exc)
    else:
        raise AssertionError("VerificationError esperado")


def test_verify_program_checks_jump_targets():
    program = _plan(
        Instruction(Opcode.JMP, 5),
        Instruction(Opcode.HALT, 0),
    )
    try:
        verify_program(program)
    except VerificationError as exc:
        assert "target" in str(exc)
    else:
        raise AssertionError("VerificationError esperado")
