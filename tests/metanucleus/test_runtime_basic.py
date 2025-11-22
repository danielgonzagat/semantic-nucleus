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
