import pytest

from metanucleus import MetaRuntime, MetaState


@pytest.fixture()
def runtime():
    return MetaRuntime(state=MetaState())


def test_runtime_echoes_text(runtime):
    output = runtime.handle_request("Oi Metanúcleo, teste determinístico.")
    assert "[META]" in output
    assert "Oi Metanúcleo"[:5] in output
