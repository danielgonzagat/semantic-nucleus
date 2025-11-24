import sys

from metanucleus.cli import auto_debug


def test_auto_debug_succeeds_on_first_try(monkeypatch):
    calls = []

    def fake_run(cmd, env):
        calls.append(cmd)
        return 0

    rc = auto_debug.run_cycle(
        pytest_args=["-k", "smoke"],
        domains=["all"],
        max_cycles=2,
        skip_auto_evolve=False,
        keep_memory=False,
        runner=fake_run,
    )
    assert rc == 0
    assert len(calls) == 1
    assert calls[0][:3] == [sys.executable, "-m", "pytest"]


def test_auto_debug_runs_auto_evolve_between_failures(monkeypatch):
    state = {"pytest_calls": 0}
    commands = []

    def sequenced_runner(cmd, env):
        commands.append(cmd)
        if "pytest" in cmd:
            state["pytest_calls"] += 1
            return 1 if state["pytest_calls"] == 1 else 0
        if "metanucleus-auto-evolve" in cmd:
            return 0
        return 0

    rc = auto_debug.run_cycle(
        pytest_args=[],
        domains=["all"],
        max_cycles=2,
        skip_auto_evolve=False,
        keep_memory=True,
        runner=sequenced_runner,
    )
    assert rc == 0
    assert commands.count(["metanucleus-auto-evolve", "all", "--apply"]) == 1


def test_auto_debug_respects_skip_auto_evolve(monkeypatch):
    def always_fail(cmd, env):
        return 1

    rc = auto_debug.run_cycle(
        pytest_args=[],
        domains=["all"],
        max_cycles=3,
        skip_auto_evolve=True,
        keep_memory=False,
        runner=always_fail,
    )
    assert rc == 1
