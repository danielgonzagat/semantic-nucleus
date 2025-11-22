from metanucleus.core.ast_bridge import python_code_to_liu, liu_to_python_code


def test_python_code_to_liu_captures_function():
    code = """
def soma(a, b):
    c = a + b
    return c
"""
    liu_module = python_code_to_liu(code)
    assert liu_module.fields["kind"].label == "py_module"
    body = liu_module.fields["body"].args
    assert len(body) == 1
    fn = body[0]
    assert fn.fields["kind"].label == "py_function"
    assert fn.fields["name"].label == "soma"


def test_roundtrip_simple_function():
    code = """
def inc(x):
    return x + 1
"""
    liu_module = python_code_to_liu(code)
    regenerated = liu_to_python_code(liu_module)
    assert "def inc" in regenerated
    assert "return" in regenerated
