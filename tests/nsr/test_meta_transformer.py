import pytest

from nsr import MetaTransformer, MetaRoute, SessionCtx, run_text_full
from nsr.meta_transformer import build_meta_summary, meta_summary_to_dict
from svm.opcodes import Opcode


def test_meta_transformer_routes_math():
    session = SessionCtx()
    transformer = MetaTransformer(session)
    result = transformer.transform("2+2")
    assert result.route is MetaRoute.MATH
    assert result.preseed_answer is not None
    assert result.trace_label and result.trace_label.startswith("MATH[")
    assert session.language_hint == result.language_hint
    assert result.calc_plan is not None
    assert [inst.opcode for inst in result.calc_plan.program.instructions] == [
        Opcode.PUSH_CONST,
        Opcode.STORE_ANSWER,
        Opcode.HALT,
    ]


def test_meta_transformer_routes_logic():
    session = SessionCtx()
    transformer = MetaTransformer(session)
    result = transformer.transform("FACT chuva")
    assert result.route is MetaRoute.LOGIC
    assert result.preseed_answer is not None
    assert result.trace_label == "LOGIC[FACT]"
    assert session.logic_engine is not None


def test_meta_transformer_routes_instinct():
    session = SessionCtx()
    transformer = MetaTransformer(session)
    result = transformer.transform("oi, tudo bem?")
    assert result.route is MetaRoute.INSTINCT
    assert result.preseed_quality and result.preseed_quality > 0.8
    assert result.trace_label and result.trace_label.startswith("IAN[")
    assert session.language_hint == result.language_hint


def test_meta_transformer_falls_back_to_text_route():
    session = SessionCtx()
    transformer = MetaTransformer(session)
    result = transformer.transform("O carro tem roda")
    assert result.route is MetaRoute.TEXT
    assert result.preseed_answer is None
    assert result.trace_label is None
    assert result.preseed_context is not None
    tags = {dict(node.fields)["tag"].label for node in result.preseed_context}
    assert "meta_route" in tags
    assert "meta_input" in tags
    language_field = dict(result.struct_node.fields).get("language")
    assert language_field is not None
    assert (language_field.label or "").startswith("pt")
    lc_meta = dict(result.struct_node.fields).get("lc_meta")
    assert lc_meta is not None
    assert result.lc_meta is lc_meta
    lc_fields = dict(lc_meta.fields)
    assert lc_fields["tag"].label == "lc_meta"
    assert lc_fields["language"].label == "pt"
    assert result.calc_plan is not None
    assert [inst.opcode for inst in result.calc_plan.program.instructions] == [
        Opcode.PHI_NORMALIZE,
        Opcode.PHI_SUMMARIZE,
        Opcode.HALT,
    ]
    context_tags = [dict(node.fields)["tag"].label for node in result.preseed_context]
    assert "lc_meta" in context_tags


def test_meta_transformer_routes_code_snippet():
    session = SessionCtx()
    transformer = MetaTransformer(session)
    code_text = """
def soma(x, y):
    return x + y
"""
    result = transformer.transform(code_text)
    assert result.route is MetaRoute.CODE
    assert result.preseed_answer is not None
    assert result.trace_label == "CODE[PYTHON]"
    assert result.preseed_quality and result.preseed_quality >= 0.85
    assert any((dict(node.fields)["tag"].label == "meta_route") for node in result.preseed_context)
    plan = result.calc_plan
    assert plan is not None
    assert plan.route is MetaRoute.CODE
    assert len(plan.program.constants) == 1
    assert plan.program.constants[0] == result.preseed_answer
    assert [inst.opcode for inst in plan.program.instructions] == [
        Opcode.PUSH_CONST,
        Opcode.STORE_ANSWER,
        Opcode.HALT,
    ]


def test_meta_transformer_text_route_uses_lc_calculus_pipeline(monkeypatch):
    session = SessionCtx()
    transformer = MetaTransformer(session)

    for target in (
        "maybe_route_math",
        "maybe_route_logic",
        "maybe_route_code",
        "maybe_route_text",
    ):
        monkeypatch.setattr(f"nsr.meta_transformer.{target}", lambda *args, **kwargs: None)

    result = transformer.transform("como você está?")
    assert result.route is MetaRoute.TEXT
    assert result.calc_plan is not None
    opcodes = [inst.opcode for inst in result.calc_plan.program.instructions]
    assert opcodes == [
        Opcode.PHI_NORMALIZE,
        Opcode.PHI_INFER,
        Opcode.PHI_SUMMARIZE,
        Opcode.PUSH_CONST,
        Opcode.STORE_ANSWER,
        Opcode.HALT,
    ]
    assert result.calc_plan.description == "text_phi_state_query"
    constants = result.calc_plan.program.constants
    assert len(constants) == 1
    calc_payload = dict(constants[0].fields)["payload"]
    assert dict(calc_payload.fields)["operator"].label == "STATE_QUERY"


def test_text_route_appends_lc_meta_calc_to_context(monkeypatch):
    for target in (
        "maybe_route_math",
        "maybe_route_logic",
        "maybe_route_code",
        "maybe_route_text",
    ):
        monkeypatch.setattr(f"nsr.meta_transformer.{target}", lambda *args, **kwargs: None)
    outcome = run_text_full("como você está?", session=SessionCtx())
    tags = [dict(node.fields).get("tag").label for node in outcome.isr.context if dict(node.fields).get("tag")]
    assert "lc_meta_calc" in tags
    assert outcome.calc_result is not None
    assert outcome.calc_result.answer is not None


def test_meta_summary_includes_meta_calculation(monkeypatch):
    session = SessionCtx()
    transformer = MetaTransformer(session)
    for target in (
        "maybe_route_math",
        "maybe_route_logic",
        "maybe_route_code",
        "maybe_route_text",
    ):
        monkeypatch.setattr(f"nsr.meta_transformer.{target}", lambda *args, **kwargs: None)
    meta_result = transformer.transform("como você está?")
    summary_nodes = build_meta_summary(meta_result, "placeholder", 0.8, "QUALITY_THRESHOLD")
    summary_dict = meta_summary_to_dict(summary_nodes)
    calc_json = summary_dict.get("meta_calculation")
    assert calc_json
    assert '"label":"STATE_QUERY"' in calc_json
