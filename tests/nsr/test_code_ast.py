from nsr.code_ast import (
    build_python_ast_meta,
    build_rust_ast_meta,
    build_js_ast_meta,
    build_elixir_ast_meta,
)


def test_build_python_ast_meta_returns_struct():
    source = """
def soma(x, y):
    return x + y
"""
    ast_node = build_python_ast_meta(source)
    assert ast_node is not None
    fields = dict(ast_node.fields)
    assert fields["tag"].label == "code_ast"
    assert fields["language"].label == "python"
    assert fields["node_count"].value >= 1
    root = fields["root"]
    root_fields = dict(root.fields)
    assert root_fields["type"].label == "Module"


def test_build_python_ast_meta_handles_invalid_source():
    ast_node = build_python_ast_meta("not : valid python")
    assert ast_node is None


def test_build_rust_ast_meta_serializes_outline():
    items = [
        {
            "kind": "fn",
            "name": "soma",
            "params": [{"name": "x", "type": "i32"}, {"name": "y", "type": "i32"}],
            "ret": "i32",
            "body": "x + y",
        }
    ]
    ast_node = build_rust_ast_meta(items, "fn soma(x: i32, y: i32) -> i32 { x + y }")
    fields = dict(ast_node.fields)
    assert fields["language"].label == "rust"
    assert fields["node_count"].value == 1
    functions = fields["functions"]
    fn_struct = functions.args[0]
    fn_fields = dict(fn_struct.fields)
    assert fn_fields["name"].label == "soma"


def test_build_js_ast_meta_serializes_outline():
    items = [
        {
            "name": "sum",
            "params": [{"name": "x", "type": ""}],
            "body": "return x + 1;",
        }
    ]
    ast_node = build_js_ast_meta(items, "function sum(x) { return x + 1; }")
    fields = dict(ast_node.fields)
    assert fields["language"].label == "javascript"
    assert fields["node_count"].value == 1


def test_build_elixir_ast_meta_serializes_outline():
    items = [
        {
            "name": "soma",
            "params": [{"name": "x", "type": ""}, {"name": "y", "type": ""}],
            "body": "x + y",
        }
    ]
    ast_node = build_elixir_ast_meta(items, "def soma(x, y) do\nx + y\nend")
    fields = dict(ast_node.fields)
    assert fields["language"].label == "elixir"
    assert fields["node_count"].value == 1
