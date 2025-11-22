from liu import entity, operation, struct

from nsr.code_ast import build_python_ast_meta, build_js_ast_meta
from nsr.operators import apply_operator
from nsr.state import SessionCtx, initial_isr


def _make_isr_with_code_ast(code_ast):
    session = SessionCtx()
    base_struct = struct(tag=entity("test_input"))
    isr = initial_isr(base_struct, session)
    isr.context = tuple((*isr.context, code_ast))
    return isr, session


def test_rewrite_code_operator_handles_python_ast():
    code_ast = build_python_ast_meta(
        """
def soma(x, y):
    return x + y
"""
    )
    isr, session = _make_isr_with_code_ast(code_ast)
    updated = apply_operator(isr, operation("REWRITE_CODE"), session)
    assert updated is not isr
    summaries = [node for node in updated.context if dict(node.fields).get("tag").label == "code_ast_summary"]
    assert summaries
    relations = [rel for rel in updated.relations if (rel.label or "") == "code/FUNCTION_COUNT"]
    assert relations


def test_rewrite_code_operator_handles_js_outline():
    ast = build_js_ast_meta(
        [
            {"name": "sum", "params": [{"name": "x", "type": ""}], "body": "return x + 1;", "ret": ""},
            {"name": "mul", "params": [{"name": "x", "type": ""}, {"name": "y", "type": ""}], "body": "return x * y;", "ret": ""},
        ],
        "function sum(x) { return x + 1; }",
    )
    isr, session = _make_isr_with_code_ast(ast)
    updated = apply_operator(isr, operation("REWRITE_CODE"), session)
    summaries = [node for node in updated.context if dict(node.fields).get("tag").label == "code_ast_summary"]
    assert summaries
    fn_counts = [rel.args[1].value for rel in updated.relations if (rel.label or "") == "code/FUNCTION_COUNT"]
    assert any(value == 2 for value in fn_counts)
