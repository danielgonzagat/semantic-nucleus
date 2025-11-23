from liu import NodeKind

from nsr import SessionCtx, run_text, run_text_full
from nsr.meta_memory import build_meta_memory


def test_meta_memory_aggregates_history_and_current_entry():
    session = SessionCtx()
    outcome = run_text_full("Um carro existe", session)
    assert outcome.meta_summary is not None
    history = [outcome.meta_summary]
    current_entry = {
        "route": "text",
        "answer": "Nova resposta determinística.",
        "expression_preview": "Nova resposta determinística.",
        "expression_answer_digest": "digest::current",
        "reasoning_trace_digest": "trace::current",
    }
    node = build_meta_memory(history, current_entry, limit=2)
    assert node is not None
    fields = dict(node.fields)
    assert fields["tag"].label == "meta_memory"
    assert int(fields["size"].value) == 2
    entries = fields["entries"]
    assert entries.kind.name == "LIST"
    assert len(entries.args) == 2
    first_entry_fields = dict(entries.args[0].fields)
    assert first_entry_fields["route"].label
    assert first_entry_fields["answer_preview"].label
    assert first_entry_fields["reasoning_digest"].label is not None


def test_meta_memory_persistence_roundtrip(tmp_path):
    store = tmp_path / "memory.jsonl"
    session = SessionCtx()
    session.config.memory_store_path = str(store)
    run_text("Um carro existe", session)
    assert store.exists()
    new_session = SessionCtx()
    new_session.config.memory_store_path = str(store)
    outcome = run_text_full("O carro tem roda", new_session)
    assert any("Φ_MEMORY[RECALL]" in step for step in outcome.trace.steps)
