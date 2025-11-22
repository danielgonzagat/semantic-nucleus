import pytest

from metanucleus import MetaRuntime, MetaState


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


def test_state_command_shows_context(runtime):
    runtime.handle_request("Oi Metanúcleo!")
    state_output = runtime.handle_request("/state")
    assert "Estado" in state_output
    assert "Oi Metanúcleo"[:5] in state_output
