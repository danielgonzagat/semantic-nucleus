from metanucleus.core.sandbox import MetaSandbox
from metanucleus.runtime.meta_runtime import MetaRuntime
from metanucleus.core.state import MetaState


def test_sandbox_snapshot_isolated():
    base_state = MetaState()
    runtime = MetaRuntime(state=base_state)
    runtime.handle_request("Oi Metanúcleo!")
    original_context = list(runtime.state.isr.context)

    sandbox = MetaSandbox.from_state(runtime.state)
    sand_runtime = sandbox.spawn_runtime()
    sand_runtime.handle_request("Teste isolado.")

    assert len(runtime.state.isr.context) == len(original_context)
    assert runtime.state.isr.context[-1].fields.get("raw").label == "Oi Metanúcleo!"
