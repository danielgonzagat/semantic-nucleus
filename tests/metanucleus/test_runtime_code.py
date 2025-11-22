import pytest

from metanucleus import MetaRuntime, MetaState


@pytest.fixture()
def runtime():
    return MetaRuntime(state=MetaState())


def test_runtime_handles_python_code(runtime):
    code = """
def soma(a, b):
    return a + b
"""
    runtime.handle_request(code)
    msg = runtime.state.isr.context[-1]
    assert msg.fields["kind"].label == "code_snippet"
    ast_node = msg.fields["ast"]
    assert ast_node.fields["kind"].label == "py_module"
    assert "def soma" in runtime.state.meta_history[-1]["input"]


def test_code_input_still_produces_answer(runtime):
    code = "def inc(x): return x + 1"
    output = runtime.handle_request(code)
    assert "code snippet" in output.lower() or "trecho de código" in output.lower()
