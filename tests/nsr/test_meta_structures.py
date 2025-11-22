from nsr.meta_structures import (
    build_lc_meta_struct,
    lc_term_to_node,
    meta_calculation_to_node,
)
from nsr.lc_omega import LCTerm, MetaCalculation, lc_parse


def test_lc_term_to_node_serializes_tree():
    term = LCTerm(
        kind="SEQ",
        children=(
            LCTerm(kind="SYM", label="A"),
            LCTerm(kind="SYM", label="B"),
        ),
    )
    node = lc_term_to_node(term)
    fields = dict(node.fields)
    assert fields["kind"].label == "SEQ"
    children = fields.get("children")
    assert children is not None
    assert len(children.args) == 2
    assert dict(children.args[0].fields)["kind"].label == "SYM"


def test_meta_calculation_to_node_includes_operands():
    operand = LCTerm(kind="SYM", label="STATE_GOOD")
    calc = MetaCalculation(operator="STATE_ASSERT", operands=(operand,))
    node = meta_calculation_to_node(calc)
    fields = dict(node.fields)
    assert fields["tag"].label == "meta_calculation"
    assert fields["operator"].label == "STATE_ASSERT"
    operands = fields["operands"]
    assert operands.kind.name == "LIST"
    assert operands.args[0].kind.name == "STRUCT"


def test_build_lc_meta_struct_includes_calculus():
    result = lc_parse("pt", "como você está?")
    meta_node = build_lc_meta_struct(result)
    fields = dict(meta_node.fields)
    assert fields["tag"].label == "lc_meta"
    assert fields["language"].label == "pt"
    assert fields["pattern"].label == "QUESTION_HEALTH_VERBOSE"
    calculus = fields["calculus"]
    calc_fields = dict(calculus.fields)
    assert calc_fields["operator"].label == "STATE_QUERY"
    operands = calc_fields["operands"]
    assert operands.kind.name == "LIST"
    assert operands.args[0].kind.name == "STRUCT"
