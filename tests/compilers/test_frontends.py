from frontend_python.compiler import compile_source as compile_py
from frontend_elixir.compiler import compile_module as compile_ex
from frontend_rust.compiler import compile_items as compile_rust
from frontend_logic.compiler import compile_logic


def test_python_frontend_produces_defn():
    code = """
def soma(x, y):
    return x + y
"""
    rels = compile_py(code)
    assert any(rel.label == "code/DEFN" for rel in rels)


def test_elixir_frontend():
    rels = compile_ex("Math", {"functions": [{"name": "inc", "params": ["x"], "body": "x + 1"}]})
    assert rels and rels[0].label == "code/DEFN"


def test_rust_frontend():
    rels = compile_rust("core", [{"kind": "fn", "name": "add", "params": [{"name": "a"}, {"name": "b"}], "ret": "i32"}])
    assert any(rel.label == "code/RETURNS" for rel in rels)


def test_logic_compiler():
    facts, rules = compile_logic(
        """
        pai(joao, maria).
        pai(X, Y) :- genitor(X, Y).
        """
    )
    assert len(facts) == 1
    assert rules and rules[0].conclusion.label == "pai"
