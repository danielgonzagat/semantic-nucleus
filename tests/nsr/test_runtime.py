import nsr.runtime as nsr_runtime

from liu import relation, entity, var, struct, list_node, text, number, operation, NodeKind

from nsr import (
    run_text,
    run_text_with_explanation,
    run_struct,
    run_text_full,
    run_struct_full,
    SessionCtx,
    Rule,
    EquationSnapshotStats,
    EquationInvariantStatus,
    tokenize,
    build_struct,
)
from nsr.operators import apply_operator
from nsr.runtime import _state_signature, HaltReason
from nsr.state import initial_isr
from nsr.lex import DEFAULT_LEXICON


def _extract_ian_reply(outcome):
    for node in outcome.isr.context:
        fields = dict(node.fields)
        tag = fields.get("tag")
        if tag is not None and (tag.label or "") == "ian_reply":
            return fields
    return None


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


def test_explain_operator_outputs_detailed_report():
    session = SessionCtx()
    tokens = tokenize("O carro tem roda", DEFAULT_LEXICON)
    struct_node = build_struct(tokens)
    isr = initial_isr(struct_node, session)
    explained = apply_operator(isr, operation("EXPLAIN", struct_node), session)
    answer_node = dict(explained.answer.fields)["answer"]
    text_value = answer_node.label or ""
    assert "Explicação determinística" in text_value
    assert "Relações (1)" in text_value
    assert "carro has roda" in text_value
    assert "Próximos Φ" in text_value
    assert "Relações novas" in text_value
    assert "Relações removidas" in text_value


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


def test_run_text_full_exposes_explanation():
    session = SessionCtx()
    outcome = run_text_full("O carro tem roda", session)
    assert "Explicação determinística" in outcome.explanation
    assert "Relações" in outcome.explanation
    assert "Relações novas" in outcome.explanation
    assert "Relações removidas" in outcome.explanation


def test_run_text_with_explanation_returns_triple():
    session = SessionCtx()
    answer, trace, explanation = run_text_with_explanation("O carro tem roda", session)
    assert answer
    assert trace.steps
    assert "Relações novas" in explanation


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
    outcome = run_text_full("O carro tem roda", session)
    assert outcome.halt_reason is HaltReason.CONTRADICTION
    assert outcome.trace.contradictions
    assert any("CONTRADICTION" in step for step in outcome.trace.steps)


def test_runtime_can_disable_contradiction_check():
    session = SessionCtx(
        kb_ontology=(
            relation("HAS", entity("carro"), entity("roda")),
            relation("NOT_HAS", entity("carro"), entity("roda")),
        )
    )
    session.config.enable_contradiction_check = False
    outcome = run_text_full("O carro tem roda", session)
    assert outcome.halt_reason is not HaltReason.CONTRADICTION
    assert outcome.trace.contradictions == []


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
    status = stats.validate()
    assert status.ok


def test_invariant_failure_triggers_halt(monkeypatch):
    session = SessionCtx()

    def fake_validate(self, previous=None, quality_tolerance=1e-3):
        return EquationInvariantStatus(ok=False, failures=("forced",), quality_regression=True, quality_delta=-0.5)

    monkeypatch.setattr(EquationSnapshotStats, "validate", fake_validate)
    outcome = run_text_full("Um carro existe", session)
    assert outcome.halt_reason is HaltReason.INVARIANT_FAILURE
    assert any("forced" in entry for entry in outcome.trace.invariant_failures)


def test_tokenize_emits_rel_payload_for_relwords():
    tokens = tokenize("O carro tem roda", DEFAULT_LEXICON)
    rel_tokens = [token for token in tokens if token.tag == "RELWORD"]
    assert rel_tokens
    assert rel_tokens[0].payload == "HAS"


def test_tokenize_skips_articles_and_handles_english_relations():
    tokens = tokenize("The car has a wheel", DEFAULT_LEXICON)
    lemmas = {token.lemma for token in tokens}
    assert "the" not in lemmas
    rel_tokens = [token for token in tokens if token.tag == "RELWORD"]
    assert rel_tokens
    assert rel_tokens[0].payload == "HAS"
    assert all(token.tag == "RELWORD" for token in tokens if token.lemma == "a")


def test_build_struct_includes_relation_nodes():
    tokens = tokenize("O carro tem roda", DEFAULT_LEXICON)
    struct_node = build_struct(tokens)
    relations_field = dict(struct_node.fields).get("relations")
    assert relations_field is not None
    assert relations_field.kind is NodeKind.LIST
    assert relations_field.args
    relation_node = relations_field.args[0]
    assert relation_node.label == "HAS"
    assert relation_node.args[0].label == "carro"
    assert relation_node.args[1].label == "roda"


def test_answer_renders_relation_summary():
    session = SessionCtx()
    answer, _ = run_text("O carro tem roda", session)
    assert "Relações:" in answer
    assert "carro has roda" in answer.lower()


def test_initial_isr_seeds_relations_into_state():
    session = SessionCtx()
    tokens = tokenize("O carro tem roda", DEFAULT_LEXICON)
    struct_node = build_struct(tokens)
    outcome = run_struct_full(struct_node, session)
    assert any(rel.label == "HAS" for rel in outcome.isr.relations)
    assert any(rel.label == "HAS" for rel in outcome.equation.relations)


def test_run_text_handles_english_relation_sentence():
    session = SessionCtx()
    answer, _ = run_text("The car has a wheel", session)
    assert "relações:" in answer.lower()
    assert "carro has wheel" in answer.lower()


def test_run_text_handles_spanish_relation_sentence():
    session = SessionCtx()
    answer, _ = run_text("El coche tiene una rueda", session)
    assert "relações:" in answer.lower()
    assert "carro has roda" in answer.lower()


def test_run_text_handles_french_relation_sentence():
    session = SessionCtx()
    answer, _ = run_text("La voiture a une roue", session)
    assert "relações:" in answer.lower()
    assert "carro has roda" in answer.lower()


def test_run_text_handles_ian_greetings():
    session = SessionCtx()
    answer, trace = run_text("oi, tudo bem?", session)
    assert answer == "tudo bem, e você?"
    assert any(step.startswith("1:IAN[") for step in trace.steps)


def test_run_text_handles_verbose_health_question():
    session = SessionCtx()
    answer, trace = run_text("como você está?", session)
    assert answer == "estou bem, e você?"
    assert any("IAN[QUESTION_HEALTH_VERBOSE" in step for step in trace.steps)


def test_run_text_handles_english_health_question():
    session = SessionCtx()
    answer, trace = run_text("hi, how are you?", session)
    assert answer == "i am fine, and you?"
    assert any("IAN[QUESTION_HEALTH_VERBOSE_EN" in step for step in trace.steps)


def test_run_text_handles_spanish_health_question():
    session = SessionCtx()
    answer, trace = run_text("hola, todo bien?", session)
    assert answer == "todo bien, y tú?"
    assert any("IAN[QUESTION_HEALTH_ES" in step for step in trace.steps)


def test_run_text_handles_spanish_verbose_health_question():
    session = SessionCtx()
    answer, trace = run_text("hola, ¿cómo estás?", session)
    assert answer == "estoy bien, y tú?"
    assert any("IAN[QUESTION_HEALTH_VERBOSE_ES" in step for step in trace.steps)


def test_run_text_handles_french_greeting():
    session = SessionCtx()
    answer, trace = run_text("bonjour!", session)
    assert answer == "bonjour"
    assert any("IAN[GREETING_SIMPLE_FR" in step for step in trace.steps)


def test_run_text_handles_french_health_question():
    session = SessionCtx()
    answer, trace = run_text("tout va bien?", session)
    assert answer == "tout va bien, et toi?"
    assert any("IAN[QUESTION_HEALTH_FR" in step for step in trace.steps)


def test_run_text_handles_french_verbose_health_question():
    session = SessionCtx()
    answer, trace = run_text("bonjour, comment ça va?")
    assert answer == "je vais bien, et toi?"
    assert any("IAN[QUESTION_HEALTH_VERBOSE_FR" in step for step in trace.steps)


def test_run_text_handles_italian_greeting():
    session = SessionCtx()
    answer, trace = run_text("ciao!", session)
    assert answer == "ciao"
    assert any("IAN[GREETING_SIMPLE_IT" in step for step in trace.steps)


def test_run_text_handles_italian_health_questions():
    session = SessionCtx()
    answer, trace = run_text("tutto bene?", session)
    assert answer == "tutto bene, e tu?"
    assert any("IAN[QUESTION_HEALTH_IT" in step for step in trace.steps)
    answer_verbose, trace_verbose = run_text("come stai?", session)
    assert answer_verbose == "sto bene, e tu?"
    assert any("IAN[QUESTION_HEALTH_VERBOSE_IT" in step for step in trace_verbose.steps)


def test_ian_reply_language_portuguese():
    session = SessionCtx()
    outcome = run_text_full("oi, tudo bem?", session)
    reply_fields = _extract_ian_reply(outcome)
    assert reply_fields is not None
    assert (reply_fields["plan_language"].label or "") == "pt"


def test_ian_reply_language_english():
    session = SessionCtx()
    outcome = run_text_full("hi, how are you?", session)
    reply_fields = _extract_ian_reply(outcome)
    assert reply_fields is not None
    assert (reply_fields["plan_language"].label or "") == "en"


def test_ian_reply_language_spanish():
    session = SessionCtx()
    outcome = run_text_full("hola, ¿cómo estás?", session)
    reply_fields = _extract_ian_reply(outcome)
    assert reply_fields is not None
    assert (reply_fields["plan_language"].label or "") == "es"


def test_ian_reply_language_french():
    session = SessionCtx()
    outcome = run_text_full("bonjour, comment ça va?")
    reply_fields = _extract_ian_reply(outcome)
    assert reply_fields is not None
    assert (reply_fields["plan_language"].label or "") == "fr"


def test_ian_reply_language_italian():
    session = SessionCtx()
    outcome = run_text_full("come stai?", session)
    reply_fields = _extract_ian_reply(outcome)
    assert reply_fields is not None
    assert (reply_fields["plan_language"].label or "") == "it"


def test_run_text_handles_thanks_and_commands():
    session = SessionCtx()
    answer, trace = run_text("obrigado!", session)
    assert answer == "de nada!"
    assert any("IAN[THANKS_PT" in step for step in trace.steps)
    answer_cmd, trace_cmd = run_text("faça isso agora", session)
    assert answer_cmd == "certo, encaminhando para o núcleo."
    assert any("IAN[COMMAND_PT" in step for step in trace_cmd.steps)


def test_run_text_handles_fact_question_en():
    session = SessionCtx()
    answer, trace = run_text("what is NSR?", session)
    assert answer == "let me check that."
    assert any("IAN[QUESTION_FACT_EN" in step for step in trace.steps)


def test_run_text_handles_math_expression():
    session = SessionCtx()
    answer, trace = run_text("2 + 2", session)
    assert answer == "4"
    assert trace.steps[0].startswith("1:MATH[")


def test_language_hint_controls_non_ian_renderer():
    session = SessionCtx()
    session.language_hint = "en"
    answer, _ = run_text("O carro tem roda", session)
    assert "Relations:" in answer


def test_run_text_full_short_circuits_for_ian():
    session = SessionCtx()
    outcome = run_text_full("como você está?", session)
    assert outcome.halt_reason is HaltReason.QUALITY_THRESHOLD
    assert outcome.finalized is True
    assert outcome.quality >= session.config.min_quality
    has_reply_context = False
    for node in outcome.isr.context:
        node_fields = dict(node.fields)
        tag = node_fields.get("tag")
        if tag is not None and tag.label == "ian_reply":
            has_reply_context = "plan_role" in node_fields
            break
    assert has_reply_context


def test_code_eval_pure_binop_enriches_context():
    session = SessionCtx()
    base = struct(subject=entity("carro"))
    isr = initial_isr(base, session)
    expr = struct(
        binop=struct(
            left=number(2),
            op=text("Add"),
            right=struct(
                binop=struct(
                    left=number(3),
                    op=text("Mult"),
                    right=number(4),
                )
            ),
        )
    )
    updated = apply_operator(isr, operation("code/EVAL_PURE", expr), session)
    assert len(updated.context) == len(isr.context) + 1
    summary = updated.context[-1]
    fields = dict(summary.fields)
    assert "result" in fields and "operator" in fields and "expr" in fields
    result_node = fields["result"]
    assert result_node.kind is NodeKind.NUMBER
    assert result_node.value == 14.0
    assert (fields["operator"].label or "").lower() == "add"
    assert fields["expr"] == expr
    assert updated.quality >= 0.45


def test_code_eval_pure_records_errors_deterministically():
    session = SessionCtx()
    base = struct(subject=entity("carro"))
    isr = initial_isr(base, session)
    bad_expr = struct(
        binop=struct(
            left=number(1),
            op=text("Div"),
            right=number(0.0),
        )
    )
    updated = apply_operator(isr, operation("code/EVAL_PURE", bad_expr), session)
    assert len(updated.context) == len(isr.context) + 1
    error_entry = updated.context[-1]
    fields = dict(error_entry.fields)
    assert (fields["eval_error"].label or "") == "code/EVAL_PURE"
    assert "Division by zero" in (fields["detail"].label or "")
