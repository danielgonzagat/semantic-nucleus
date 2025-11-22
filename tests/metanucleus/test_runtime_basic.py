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
