import json

from metanucleus.core.state import MetaState
from metanucleus.runtime.meta_runtime import MetaRuntime


def test_evolve_command_generates_patch(tmp_path):
    runtime = MetaRuntime(state=MetaState())
    target_file = tmp_path / "sample_module.py"
    target_file.write_text(
        "\n"
        "def redundant(x):\n"
        "    return (x * 2) + (x * 2)\n",
        encoding="utf-8",
    )

    output = runtime.handle_request(f"/evolve {target_file}:redundant suite=none")

    assert "META-EVOLVE" in output
    assert "Evolução bem-sucedida" in output
    patch_file = target_file.with_suffix(".py.meta.patch")
    assert patch_file.exists()
    diff_contents = patch_file.read_text(encoding="utf-8")
    assert "return (x * 2) + (x * 2)" in diff_contents
    assert "return 4 * x" in diff_contents
    assert "tests: skipped" in output
    assert runtime.state.evolution_log
    event = runtime.state.evolution_log[-1]
    assert event["status"] == "success"
    assert event["suite"] == "skipped"
    assert event["tests"] == "skipped"
    assert event["patch"].endswith(".meta.patch")


def test_evolve_command_can_run_test_suite(tmp_path):
    runtime = MetaRuntime(state=MetaState())
    target_file = tmp_path / "sample_module.py"
    target_file.write_text(
        "\n"
        "def redundant(x):\n"
        "    return (x * 2) + (x * 2)\n",
        encoding="utf-8",
    )

    output = runtime.handle_request(f"/evolve {target_file}:redundant suite=basic")

    assert "META-EVOLVE" in output
    assert "Evolução rejeitada pelos testes" in output
    patch_file = target_file.with_suffix(".py.meta.patch")
    assert not patch_file.exists()
    event = runtime.state.evolution_log[-1]
    assert event["status"] == "tests_failed"
    assert event["suite"] == "basic"
    assert event["tests"] == "fail"


def test_evolutions_command_lists_recent_events(tmp_path):
    runtime = MetaRuntime(state=MetaState())
    target_file = tmp_path / "redundant.py"
    target_file.write_text(
        "\n"
        "def redundant(x):\n"
        "    return (x * 2) + (x * 2)\n",
        encoding="utf-8",
    )

    runtime.handle_request(f"/evolve {target_file}:redundant suite=none")
    output = runtime.handle_request("/evolutions")

    assert "Últimos eventos" in output
    assert "target" in output
    assert str(target_file) in output


def test_evolve_command_with_suite_file(tmp_path):
    runtime = MetaRuntime(state=MetaState())
    target_file = tmp_path / "sample_module.py"
    target_file.write_text(
        "\n"
        "def redundant(x):\n"
        "    return (x * 2) + (x * 2)\n",
        encoding="utf-8",
    )
    suite_file = tmp_path / "suite.json"
    suite_file.write_text(
        json.dumps(
            {
                "tests": [
                    {
                        "name": "saudacao",
                        "input": "Oi Metanúcleo!",
                        "expected": {"intent": "greeting", "lang": "pt"},
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    output = runtime.handle_request(
        f"/evolve {target_file}:redundant suitefile={suite_file}"
    )

    assert "Evolução bem-sucedida" in output
    event = runtime.state.evolution_log[-1]
    assert event["suite"] == suite_file.name
    assert event["tests"] == "pass"


def test_snapshot_command_writes_file(tmp_path):
    runtime = MetaRuntime(state=MetaState())
    runtime.state.meta_history.append({"route": "text", "input": "Oi", "answer": "Olá"})
    runtime.state.evolution_log.append(
        {"target": "example.py:foo", "status": "success", "suite": "skipped", "tests": "pass", "patch": "foo.py.meta.patch", "reason": "demo"}
    )
    snapshot_path = tmp_path / "snapshot.json"

    output = runtime.handle_request(f"/snapshot export {snapshot_path}")

    assert "Snapshot exportado" in output
    data = json.loads(snapshot_path.read_text(encoding="utf-8"))
    assert data["meta_history"]
    assert data["evolution_log"]

    # import snapshot
    runtime.state.meta_history.clear()
    runtime.state.evolution_log.clear()
    output = runtime.handle_request(f"/snapshot import {snapshot_path}")
    assert "importado" in output
    assert runtime.state.meta_history
    assert runtime.state.evolution_log
