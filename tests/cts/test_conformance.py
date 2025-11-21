from frontend_python.compiler import compile_source
from liu import check
from nsr import run_text, SessionCtx
from svm import build_program_from_assembly, SigmaVM


def test_frontend_relations_are_wf():
    rels = compile_source(
        """
def energia(x):
    if x > 0:
        return x
    return 0
"""
    )
    assert any(rel.label == "code/MODULE" for rel in rels)
    for rel in rels:
        check(rel)


def test_end_to_end_components():
    answer, trace = run_text("O carro anda rapido", SessionCtx())
    assert "carro" in answer.lower()
    assert trace.digest != "0" * 32

    asm = """
    PUSH_CONST 0
    PUSH_KEY 1
    BEGIN_STRUCT 1
    STORE_ANSWER
    HALT
    """
    program = build_program_from_assembly(asm, ["Carro anda rápido.", "answer"])
    vm = SigmaVM()
    vm.load(program)
    result = vm.run()
    assert dict(result.fields)["answer"].label == "Carro anda rápido."
