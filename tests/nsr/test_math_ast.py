from nsr.math_ast import build_math_ast_node
from nsr.math_core import MathInstruction


def test_build_math_ast_node_includes_term_and_value():
    instruction = MathInstruction(
        operation="sum",
        operands=(2.0, 3.0),
        language="pt",
        expression="2 + 3",
        original="2 + 3",
    )
    node = build_math_ast_node(instruction, value=5.0)
    fields = dict(node.fields)
    assert fields["tag"].label == "math_ast"
    assert fields["language"].label == "pt"
    assert fields["expression"].label == "2 + 3"
    assert fields["operator"].label == "SUM"
    assert fields["operand_count"].value == 2
    assert fields["value"].value == 5.0
