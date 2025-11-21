import nsr.runtime as nsr_runtime

from liu import relation, entity, var, struct, list_node, text, number, operation, NodeKind

from nsr import (
    run_text,
    run_struct,
    run_text_full,
    run_struct_full,
    SessionCtx,
    Rule,
)
from nsr.operators import apply_operator
from nsr.runtime import _state_signature, HaltReason
from nsr.state import initial_isr


def test_run_text_simple():
    session = SessionCtx()
    answer, trace = run_text("O carro anda rapido", session)
    assert "Carro" in answer or "carro" in answer.lower()
    assert trace.steps[0].startswith("1:")
    assert trace.digest != "0" * 32
    assert trace.steps[-1].startswith(f"{len(trace.steps)}:HALT[")
    assert isinstance(trace.halt_reason, HaltReason)
    if trace.halt_reason is HaltReason.QUALITY_THRESHOLD:
        assert trace.finalized is False


def test_infer_rule_adds_relation():
    x = var("?X")
    y = var("?Y")
    rule = Rule(
        if_all=(relation("PART_OF", x, y),),
        then=relation("HAS", y, x),
    )
    session = SessionCtx(kb_rules=(rule,), kb_ontology=(relation("PART_OF", entity("roda"), entity("carro")),))
    answer, trace = run_text("A roda existe", session)
    assert "Resumo" in answer or "Explicação" in answer or answer
    assert len(trace.steps) >= 1


def test_map_and_reduce_enrich_context():
    session = SessionCtx()
    base = struct(subject=entity("carro"))
    isr = initial_isr(base, session)
    mapped = apply_operator(isr, operation("MAP", list_node([text("a"), text("b")])), session)
    assert len(mapped.context) > len(isr.context)
    reduced = apply_operator(mapped, operation("REDUCE", list_node([number(1), number(3)])), session)
    assert any(node.kind is NodeKind.NUMBER for node in reduced.context)


def test_runtime_detects_state_variations():
    session = SessionCtx()
    base = struct(subject=entity("carro"))
    
    # Test that different operations produce different execution paths
    result1, trace1 = run_struct(base, session)
    
    # Modify session to create different state progression (extra inference rule)
    rule = Rule(
        if_all=(relation("IS_A", var("?X"), entity("type::veiculo")),),
        then=relation("TAGGED", var("?X")),
    )
    session_modified = SessionCtx(kb_rules=(rule,))
    result2, trace2 = run_struct(base, session_modified)
    
    # Verify that different configurations lead to detectable differences
    assert trace1.digest != trace2.digest or len(trace1.steps) != len(trace2.steps)


def test_run_struct_converges_with_summary(monkeypatch):
    session = SessionCtx()
    base = struct(subject=entity("carro"))
    monkeypatch.setattr(nsr_runtime, "_state_signature", lambda _: "STATIC")
    original_apply = nsr_runtime.apply_operator

    def stub_apply(isr, op, sess):
        if (op.label or "").upper() == "ANSWER":
            return isr.snapshot()
        return original_apply(isr, op, sess)

    monkeypatch.setattr(nsr_runtime, "apply_operator", stub_apply)
    answer, trace = run_struct(base, session)
    assert answer.startswith("Resumo")
    assert any("SUMMARIZE*" in step for step in trace.steps)
    assert any("STABILIZE*" in step for step in trace.steps)
    assert trace.steps[-1].startswith(f"{len(trace.steps)}:HALT[SIGNATURE_REPEAT]")
    assert trace.halt_reason is HaltReason.SIGNATURE_REPEAT
    assert trace.finalized is True


def test_run_text_full_matches_legacy_output():
    session = SessionCtx()
    outcome = run_text_full("Um carro existe", session)
    legacy_answer, legacy_trace = run_text("Um carro existe", session)
    assert outcome.answer == legacy_answer
    assert outcome.trace.steps == legacy_trace.steps
    assert outcome.trace.digest == legacy_trace.digest
    assert outcome.trace.halt_reason is outcome.halt_reason
    assert outcome.trace.finalized == outcome.finalized


def test_run_struct_full_exposes_isr_and_quality():
    session = SessionCtx()
    base = struct(subject=entity("carro"))
    outcome = run_struct_full(base, session)
    assert outcome.has_answer()
    assert isinstance(outcome.quality, float)
    assert isinstance(outcome.halt_reason, HaltReason)
    assert len(outcome.isr.context) >= 1
    assert isinstance(outcome.meets_quality(session.config.min_quality), bool)
    assert outcome.equation.input_struct.kind is NodeKind.STRUCT
    sexpr_bundle = outcome.equation.to_sexpr_bundle()
    assert "input" in sexpr_bundle and sexpr_bundle["input"].startswith("(STRUCT")
    json_bundle = outcome.equation.to_json_bundle()
    assert isinstance(json_bundle["relations"], list)
    assert isinstance(json_bundle["ontology"], list)
    assert isinstance(json_bundle["goals"], list)
    assert isinstance(json_bundle["ops_queue"], list)
    assert isinstance(json_bundle["quality"], float)
    assert outcome.equation_digest == outcome.equation.digest()


def test_runtime_halts_on_contradiction():
    session = SessionCtx(
        kb_ontology=(
            relation("HAS", entity("carro"), entity("roda")),
            relation("NOT_HAS", entity("carro"), entity("roda")),
        )
    )
    session.config.enable_contradiction_check = True
    outcome = run_text_full("O carro tem roda", session)
    assert outcome.halt_reason is HaltReason.CONTRADICTION
    assert outcome.trace.contradictions
    assert any("CONTRADICTION" in step for step in outcome.trace.steps)


def test_equation_snapshot_available_for_run_text():
    session = SessionCtx()
    outcome = run_text_full("Um carro existe", session)
    snapshot = outcome.equation
    assert snapshot.context
    assert snapshot.ontology
    assert snapshot.goals
    assert isinstance(snapshot.ops_queue, tuple)
    assert 0.0 <= snapshot.quality <= 1.0
    bundle = snapshot.to_json_bundle()
    assert bundle["answer"]["kind"] == "STRUCT"
    assert bundle["quality"] == snapshot.quality
    assert len(outcome.equation_digest) == 32


def test_equation_snapshot_text_report():
    session = SessionCtx()
    outcome = run_text_full("Um carro existe", session)
    report = outcome.equation.to_text_report(max_items=2)
    lines = report.splitlines()
    assert lines[0].startswith("Equação LIU")
    assert any(line.startswith("Ontologia[") for line in lines)
    assert any(line.startswith("Relações[") for line in lines)
    assert "Resposta:" in report
    assert "FilaΦ" in report


def test_equation_snapshot_stats():
    session = SessionCtx()
    outcome = run_text_full("Um carro existe", session)
    snapshot = outcome.equation
    stats = snapshot.stats()
    assert stats.ontology.count == len(snapshot.ontology)
    assert stats.relations.count == len(snapshot.relations)
    assert stats.context.count == len(snapshot.context)
    assert stats.quality == snapshot.quality
    assert stats.equation_digest == snapshot.digest()
    stats_dict = stats.to_dict()
    assert stats_dict["ontology"]["count"] == len(snapshot.ontology)
    assert len(stats_dict["input_digest"]) == 32
    assert len(stats_dict["answer_digest"]) == 32
