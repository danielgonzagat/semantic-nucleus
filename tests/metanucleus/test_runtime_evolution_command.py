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
