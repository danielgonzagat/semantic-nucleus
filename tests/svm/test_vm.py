from liu import entity, struct

from svm import SigmaVM, build_program_from_assembly, decode, encode


def test_vm_struct_and_relation_ops():
    asm = """
    PUSH_CONST 2
    PUSH_TEXT 0
    NEW_STRUCT 1
    STORE_REG 0

    LOAD_REG 0
    PUSH_TEXT 3
    PUSH_CONST 4
    SET_FIELD
    STORE_REG 0

    LOAD_REG 0
    PUSH_TEXT 5
    PUSH_CONST 6
    SET_FIELD
    STORE_REG 0

    PUSH_TEXT 1
    PUSH_CONST 4
    PUSH_CONST 7
    NEW_REL 2
    ADD_REL
    HAS_REL
    STORE_REG 1

    LOAD_REG 0
    PUSH_TEXT 8
    LOAD_REG 1
    SET_FIELD
    STORE_REG 0

    LOAD_REG 0
    STORE_ANSWER
    HALT
    """
    constants = [
        "answer",  # 0
        "IS_A",  # 1
        "O carro anda rápido.",  # 2
        "subject",  # 3
        entity("carro"),  # 4
        "action",  # 5
        entity("andar"),  # 6
        entity("type::veiculo"),  # 7
        "ok",  # 8
    ]
    program = build_program_from_assembly(asm, constants)
    vm = SigmaVM()
    vm.load(program)
    result = vm.run()
    fields = dict(result.fields)
    assert fields["subject"].label == "carro"
    assert fields["action"].label == "andar"
    assert fields["ok"].value is True
    assert any(rel.label == "IS_A" for rel in vm.isr.relations)


def test_vm_phi_pipeline_and_hash():
    payload = struct(subject=entity("carro"), action=entity("andar"))
    asm = """
    PHI_NORMALIZE
    PHI_INFER
    PUSH_CONST 0
    PHI_ANSWER
    STORE_ANSWER
    HASH_STATE
    STORE_REG 0
    LOAD_REG 0
    HALT
    """
    program = build_program_from_assembly(asm, [payload])
    vm = SigmaVM()
    vm.load(program, initial_struct=payload)
    result = vm.run()
    answer_field = dict(result.fields)["answer"]
    assert "carro" in (answer_field.label or "").lower()
    assert vm.registers[0].label is not None
    assert len(vm.snapshot()["isr_digest"]) == 24


def test_encoding_roundtrip():
    asm = "NOOP\nTRAP 0\nHALT"
    program = build_program_from_assembly(asm, ["trap"])
    blob = encode(program.instructions)
    decoded = decode(blob)
    assert [inst.opcode for inst in decoded] == [inst.opcode for inst in program.instructions]
