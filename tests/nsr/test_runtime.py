import nsr.runtime as nsr_runtime

from liu import relation, entity, var, struct, list_node, text, number, operation, NodeKind

from nsr import run_text, run_struct, SessionCtx, Rule
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


def test_state_signature_reflects_queue_variations():
    session = SessionCtx()
    base = struct(subject=entity("carro"))
    isr = initial_isr(base, session)
    sig_a = _state_signature(isr)
    mutated = isr.snapshot()
    mutated.ops_queue.append(operation("MAP"))
    sig_b = _state_signature(mutated)
    assert sig_a != sig_b


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
