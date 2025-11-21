from svm import build_program_from_assembly, SigmaVM, encode, decode


def test_vm_runs_and_produces_answer():
    asm = """
    PUSH_TEXT 0
    PUSH_TEXT 1
    BUILD_STRUCT 1
    STORE_ANSWER
    HALT
    """
    program = build_program_from_assembly(asm, ["answer", "O carro anda rápido."])
    vm = SigmaVM()
    vm.load(program)
    result = vm.run()
    assert dict(result.fields)["answer"].label == "O carro anda rápido."


def test_encoding_roundtrip():
    asm = "PUSH_TEXT 0\nHALT"
    program = build_program_from_assembly(asm, ["answer"])
    blob = encode(program.instructions)
    decoded = decode(blob)
    assert [inst.opcode for inst in decoded] == [inst.opcode for inst in program.instructions]
