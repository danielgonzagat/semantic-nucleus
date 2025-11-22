from nsr.code_ast import build_python_ast_meta


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
