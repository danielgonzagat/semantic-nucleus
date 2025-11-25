from liu import NodeKind

from nsr import SessionCtx, run_text, run_text_full
from nsr.meta_memory import build_meta_memory, meta_memory_to_dict


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
        "reflection_digest": "reflect::current",
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
    assert first_entry_fields["reflection_digest"].label


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


def test_meta_memory_includes_plan_synthesis_snapshot():
    session = SessionCtx()
    outcome = run_text_full("Planeje: pesquisar -> resumir -> responder", session)
    memory = outcome.meta_memory
    assert memory is not None
    entries_node = dict(memory.fields)["entries"]
    latest = entries_node.args[-1]
    latest_fields = dict(latest.fields)
    plan_total = latest_fields.get("synthesis_plan_total")
    assert plan_total is not None and int(plan_total.value) >= 1
    sources = latest_fields.get("synthesis_plan_sources")
    assert sources is not None
    assert sources.kind.name == "LIST"
    assert sources.args


def test_meta_memory_includes_program_synthesis_snapshot():
    session = SessionCtx()
    outcome = run_text_full(
        """
def soma(a, b):
    return a + b
""",
        session,
    )
    memory = outcome.meta_memory
    assert memory is not None
    entries_node = dict(memory.fields)["entries"]
    latest = entries_node.args[-1]
    latest_fields = dict(latest.fields)
    program_total = latest_fields.get("synthesis_program_total")
    assert program_total is not None and int(program_total.value) >= 1
    sources = latest_fields.get("synthesis_program_sources")
    assert sources is not None
    assert sources.kind.name == "LIST"
    assert sources.args


def test_meta_memory_to_dict_serializes_entries():
    session = SessionCtx()
    outcome = run_text_full("Planeje: pesquisar -> resumir -> responder", session)
    node = outcome.meta_memory
    snapshot = meta_memory_to_dict(node)
    assert snapshot is not None
    assert snapshot["size"] >= 1
    entries = snapshot["entries"]
    assert entries
    last = entries[-1]
    assert last.get("synthesis_plan_total", 0) >= 1
    assert last.get("route")


def test_meta_memory_to_dict_rejects_invalid_node():
    assert meta_memory_to_dict(None) is None
