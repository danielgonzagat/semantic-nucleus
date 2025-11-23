import pytest

from metanucleus import MetaRuntime, MetaState
from metanucleus.runtime import MetanucleusRuntime


@pytest.fixture()
def runtime():
    return MetaRuntime(state=MetaState())


def test_runtime_handles_statement(runtime):
    output = runtime.handle_request("Processo determinístico em curso.")
    assert "[META] Recebi" in output


def test_runtime_handles_greeting(runtime):
    output = runtime.handle_request("Oi Metanúcleo!")
    assert "Olá! Sou o Metanúcleo" in output


def test_tokens_are_injected(runtime):
    runtime.handle_request("Teste determinístico completo.")
    isr = runtime.state.isr
    utter = isr.context[-1]
    assert utter.kind.name == "STRUCT"
    assert "tokens" in utter.fields
    tokens_struct = utter.fields["tokens"]
    assert tokens_struct.kind.name == "STRUCT"
    assert any(field.kind.name == "STRUCT" for field in tokens_struct.fields.values())


def test_question_receives_question_reply(runtime):
    output = runtime.handle_request("Pode me explicar o que é o Metanúcleo?")
    assert "Pergunta registrada" in output


def test_math_question_returns_result(runtime):
    output = runtime.handle_request("Quanto é 10 + 5?")
    assert "10 + 5 = 15" in output or "resultado é 15" in output
    facts = runtime.state.isr.relations
    assert any(name == "EQUALS" for name, _ in facts)
    assert any(name == "SAID" for name, _ in facts)


def test_facts_command_reports_relations(runtime):
    runtime.handle_request("Quanto é 7 * 3?")
    facts_output = runtime.handle_request("/facts")
    assert "EQUALS" in facts_output
    filtered = runtime.handle_request("/facts EQUALS")
    assert "SAID" not in filtered
    assert "EQUALS" in filtered
    multi_filtered = runtime.handle_request("/facts SAID EQUALS")
    assert "SAID" not in multi_filtered  # ambos filtros aplicados


def test_state_command_shows_context(runtime):
    runtime.handle_request("Oi Metanúcleo!")
    state_output = runtime.handle_request("/state")
    assert "Estado" in state_output
    assert "Oi Metanúcleo"[:5] in state_output


def test_reset_and_goals_command(runtime):
    runtime.handle_request("Qual é o plano hoje?")
    goals_output_before = runtime.handle_request("/goals")
    assert "Goals/Ops" in goals_output_before
    reset_output = runtime.handle_request("/reset")
    assert "resetado" in reset_output
    goals_output_after = runtime.handle_request("/goals")
    assert "(vazio)" in goals_output_after


def test_context_command_lists_recent(runtime):
    runtime.handle_request("Primeira frase.")
    runtime.handle_request("Segunda frase informativa.")
    context_output = runtime.handle_request("/context")
    assert "Contexto" in context_output
    assert "Segunda frase" in context_output


def test_meta_command_reports_last_summary(runtime):
    runtime.handle_request("Oi Metanúcleo!")
    meta_output = runtime.handle_request("/meta")
    assert "route=text" in meta_output
    assert "Oi Metanúcleo"[:5] in meta_output
    runtime.handle_request("Outra frase simbólica.")
    meta_multi = runtime.handle_request("/meta 2")
    assert meta_multi.count("route=text") == 2


def test_testcore_command_runs_suite(runtime):
    runtime.handle_request("Oi Metanúcleo!")
    output = runtime.handle_request("/testcore")
    assert "[TESTCORE:basic]" in output
    assert "greeting_pt" in output


def test_testcore_json_output(runtime):
    runtime.handle_request("Oi!")
    output = runtime.handle_request("/testcore json")
    assert output.startswith("{")
    assert '"total"' in output


def test_testcore_alt_suite(runtime):
    runtime.handle_request("Olá!")
    output = runtime.handle_request("/testcore math")
    assert "[TESTCORE:math]" in output
    assert "math_simple_add" in output


def test_metanucleus_session_exposes_meta_payload():
    runtime = MetanucleusRuntime()
    session = runtime.new_session()
    result = session.ask_full("Um carro existe.")
    assert result.meta_summary is not None
    assert result.meta_summary["route"] == "text"
    assert result.calc_exec is not None
    assert result.calc_exec["plan_route"] == "text"
    assert "trace_digest" in result.debug_info
