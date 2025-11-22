from liu import struct as liu_struct, entity

from nsr.meta_calculus_router import text_opcode_pipeline, text_operation_pipeline
from nsr.lc_omega import MetaCalculation, LCTerm


def _calc(operator: str) -> MetaCalculation:
    return MetaCalculation(operator=operator, operands=(LCTerm(kind="SYM", label="X"),))


def test_text_opcode_pipeline_matches_known_routes():
    pipeline = text_opcode_pipeline(_calc("STATE_QUERY"))
    assert [opcode.name for opcode in pipeline] == [
        "PHI_NORMALIZE",
        "PHI_INFER",
        "PHI_SUMMARIZE",
    ]
    fallback = text_opcode_pipeline(None)
    assert [opcode.name for opcode in fallback] == ["PHI_NORMALIZE", "PHI_SUMMARIZE"]


def test_text_operation_pipeline_attaches_struct_for_answer():
    struct_node = liu_struct(subject=entity("carro"))
    pipeline = text_operation_pipeline(_calc("STATE_ASSERT"), struct_node)
    labels = [op.label for op in pipeline]
    assert labels == ["NORMALIZE", "ANSWER", "EXPLAIN", "SUMMARIZE"]
    assert pipeline[1].args[0] is struct_node
    assert pipeline[2].args[0] is struct_node
