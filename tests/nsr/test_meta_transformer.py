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
    plan_nodes = [node for node in result.preseed_context if dict(node.fields)["tag"].label == "meta_plan"]
    assert len(plan_nodes) == 1
    plan_fields = dict(plan_nodes[0].fields)
    assert plan_fields["description"].label == "math_direct_answer"
    assert plan_fields["digest"].label
    assert any(dict(node.fields)["tag"].label == "language_profile" for node in result.preseed_context)
    math_ast_nodes = [node for node in result.preseed_context if dict(node.fields)["tag"].label == "math_ast"]
    assert math_ast_nodes
    math_ast_fields = dict(math_ast_nodes[0].fields)
    assert math_ast_fields["language"].label in {"pt", "und"}
    assert math_ast_fields["expression"].label.replace(" ", "") == "2+2"
    assert result.math_ast is not None


def test_language_detection_updates_hint_and_context(monkeypatch):
    monkeypatch.setattr("nsr.meta_transformer.maybe_route_math", lambda *args, **kwargs: None)
    session = SessionCtx()
    transformer = MetaTransformer(session)
    result = transformer.transform("The car is blue and you know it.")
    assert session.language_hint == "en"
    language_nodes = [node for node in result.preseed_context if dict(node.fields)["tag"].label == "language_profile"]
    assert language_nodes
    profile_fields = dict(language_nodes[0].fields)
    assert profile_fields["language"].label == "en"


def test_meta_transformer_routes_logic():
    session = SessionCtx()
    transformer = MetaTransformer(session)
    result = transformer.transform("FACT chuva")
    assert result.route is MetaRoute.LOGIC
    assert result.preseed_answer is not None
    assert result.trace_label == "LOGIC[FACT]"
    assert session.logic_engine is not None
    plan_nodes = [node for node in result.preseed_context if dict(node.fields)["tag"].label == "meta_plan"]
    assert len(plan_nodes) == 1
    plan_fields = dict(plan_nodes[0].fields)
    assert plan_fields["description"].label == "logic_direct_answer"
    assert plan_fields["digest"].label
    assert any(dict(node.fields)["tag"].label == "language_profile" for node in result.preseed_context)


def test_meta_transformer_routes_instinct():
    session = SessionCtx()
    transformer = MetaTransformer(session)
    result = transformer.transform("oi, tudo bem?")
    assert result.route is MetaRoute.INSTINCT
    assert result.preseed_quality and result.preseed_quality > 0.8
    assert result.trace_label and result.trace_label.startswith("IAN[")
    assert session.language_hint == result.language_hint
    plan_nodes = [node for node in result.preseed_context if dict(node.fields)["tag"].label == "meta_plan"]
    assert len(plan_nodes) == 1
    plan_fields = dict(plan_nodes[0].fields)
    assert plan_fields["description"].label == "instinct_direct_answer"
    assert plan_fields["digest"].label
    assert any(dict(node.fields)["tag"].label == "language_profile" for node in result.preseed_context)


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
    assert result.meta_calculation is None
    assert result.phi_plan_ops is None
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
    assert "meta_plan" in context_tags
    assert "language_profile" in context_tags
    plan_node = next(node for node in result.preseed_context if dict(node.fields)["tag"].label == "meta_plan")
    plan_fields = dict(plan_node.fields)
    assert plan_fields["description"].label == "text_phi_pipeline"
    assert plan_fields["digest"].label


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
    plan_nodes = [node for node in result.preseed_context if dict(node.fields)["tag"].label == "meta_plan"]
    assert len(plan_nodes) == 1
    plan_fields = dict(plan_nodes[0].fields)
    assert plan_fields["description"].label == "code_direct_answer"
    assert plan_fields["digest"].label
    assert any(dict(node.fields)["tag"].label == "language_profile" for node in result.preseed_context)
    assert any(dict(node.fields)["tag"].label == "code_ast" for node in result.preseed_context)
    assert result.code_ast is not None
    summary_nodes = [node for node in result.preseed_context if dict(node.fields)["tag"].label == "code_ast_summary"]
    assert summary_nodes, "expected code_ast_summary in preseed context"
    summary_fields = dict(summary_nodes[0].fields)
    assert summary_fields["function_count"].value >= 1
    assert summary_fields["digest"].label
    assert result.code_summary is not None
    assert dict(result.code_summary.fields)["tag"].label == "code_ast_summary"


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
    assert result.meta_calculation is not None
    assert result.meta_calculation.operator == "STATE_QUERY"
    assert result.phi_plan_ops == ("NORMALIZE", "INFER", "SUMMARIZE")
    context_tags = [dict(node.fields)["tag"].label for node in result.preseed_context]
    assert context_tags.count("meta_plan") == 1
    plan_node = next(node for node in result.preseed_context if dict(node.fields)["tag"].label == "meta_plan")
    plan_fields = dict(plan_node.fields)
    assert (plan_fields["chain"].label or "") == "NORMALIZE→INFER→SUMMARIZE"
    assert plan_fields["description"].label == "text_phi_state_query"
    assert plan_fields["digest"].label
    assert int(plan_fields["program_len"].value) == 6
    assert int(plan_fields["const_len"].value) == 1
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
    assert summary_dict["phi_plan_chain"] == "NORMALIZE→INFER→SUMMARIZE"
    assert summary_dict["phi_plan_ops"] == ["NORMALIZE", "INFER", "SUMMARIZE"]
    assert summary_dict["phi_plan_description"] == "text_phi_state_query"
    assert summary_dict["phi_plan_digest"]
    assert summary_dict["phi_plan_program_len"] == 6
    assert summary_dict["phi_plan_const_len"] == 1
    assert summary_dict["language_category"] == "text"
    assert summary_dict["language_detected"] == "pt"
    assert len(summary_dict["meta_digest"]) == 32


def test_meta_summary_includes_plan_metadata_for_math():
    session = SessionCtx()
    transformer = MetaTransformer(session)
    meta_result = transformer.transform("2+2")
    summary_nodes = build_meta_summary(meta_result, "4", meta_result.preseed_quality or 0.99, "QUALITY_THRESHOLD")
    summary_dict = meta_summary_to_dict(summary_nodes)
    assert summary_dict["phi_plan_description"] == "math_direct_answer"
    assert summary_dict["phi_plan_digest"]
    assert summary_dict["phi_plan_program_len"] == 3
    assert summary_dict["phi_plan_const_len"] == 1
    assert summary_dict["math_ast_operator"] == "EXPRESSION"
    assert summary_dict["math_ast_language"] in {"pt", "und"}
    assert summary_dict["math_ast_operand_count"] >= 1


def test_meta_summary_includes_code_ast_data():
    session = SessionCtx()
    transformer = MetaTransformer(session)
    source = """
def soma(x, y):
    return x + y
"""
    meta_result = transformer.transform(source)
    summary_nodes = build_meta_summary(meta_result, "Resumo", meta_result.preseed_quality or 0.9, "QUALITY_THRESHOLD")
    summary_dict = meta_summary_to_dict(summary_nodes)
    assert summary_dict["code_ast_language"] == "python"
    assert summary_dict["code_ast_node_count"] >= 1
    assert summary_dict["code_summary_language"] == "python"
    assert summary_dict["code_summary_function_count"] >= 1


def test_meta_summary_includes_calc_exec_snapshot():
    outcome = run_text_full("2+2", session=SessionCtx())
    assert outcome.meta_summary is not None
    tags = [dict(node.fields)["tag"].label for node in outcome.meta_summary]
    assert "meta_calc_exec" in tags
    exec_node = next(node for node in outcome.meta_summary if dict(node.fields)["tag"].label == "meta_calc_exec")
    exec_fields = dict(exec_node.fields)
    assert exec_fields["plan_route"].label == "math"
    assert exec_fields["plan_description"].label == "math_direct_answer"
    assert exec_fields["consistent"].label == "true"
    assert exec_fields["answer_fingerprint"].label
    assert exec_fields["snapshot_digest"].label
    summary_dict = meta_summary_to_dict(outcome.meta_summary)
    assert summary_dict["calc_exec_route"] == "math"
    assert summary_dict["calc_exec_description"] == "math_direct_answer"
    assert summary_dict["calc_exec_consistent"] is True
    assert summary_dict["calc_exec_snapshot_digest"]
    assert summary_dict["calc_exec_answer_fingerprint"]
    assert "math_eval" in summary_dict["calc_exec_answer"]


def test_meta_transformer_routes_rust_code():
    session = SessionCtx()
    transformer = MetaTransformer(session)
    rust_source = """
fn soma(x: i32, y: i32) -> i32 {
    x + y
}
"""
    result = transformer.transform(rust_source)
    assert result.route is MetaRoute.CODE
    assert result.trace_label == "CODE[RUST]"
    assert result.code_ast is not None
    ast_fields = dict(result.code_ast.fields)
    assert ast_fields["language"].label == "rust"
    summary_nodes = build_meta_summary(result, "Resumo", result.preseed_quality or 0.88, "QUALITY_THRESHOLD")
    summary_dict = meta_summary_to_dict(summary_nodes)
    assert summary_dict["code_ast_language"] == "rust"
    assert summary_dict["code_ast_node_count"] >= 1
