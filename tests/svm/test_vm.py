from svm import build_program_from_assembly, SigmaVM, encode, decode
from svm.opcodes import Opcode


def test_vm_runs_and_produces_answer():
    asm = """
    PUSH_CONST 1
    PUSH_KEY 0
    BEGIN_STRUCT 1
    STORE_ANSWER
    HALT
    """
    program = build_program_from_assembly(asm, ["answer", "O carro anda rápido."])
    vm = SigmaVM()
    vm.load(program)
    result = vm.run()
    assert dict(result.fields)["answer"].label == "O carro anda rápido."


def test_register_instructions_roundtrip():
    asm = """
    PUSH_CONST 0
    STORE_REG 0
    LOAD_REG 0
    PUSH_KEY 1
    BEGIN_STRUCT 1
    STORE_ANSWER
    HALT
    """
    program = build_program_from_assembly(asm, ["O carro anda rápido.", "answer"])
    vm = SigmaVM()
    vm.load(program)
    result = vm.run()
    answer = dict(result.fields)["answer"].label
    assert answer == "O carro anda rápido."


def test_encoding_roundtrip():
    asm = "NOOP\nHALT"
    program = build_program_from_assembly(asm, [])
    blob = encode(program.instructions)
    decoded = decode(blob)
    assert [inst.opcode for inst in decoded] == [inst.opcode for inst in program.instructions]
