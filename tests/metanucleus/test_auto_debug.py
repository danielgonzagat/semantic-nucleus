import sys
from pathlib import Path

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


def test_auto_debug_reports_when_enabled(monkeypatch):
    report_calls = []

    def fake_render(root, targets, as_json):
        report_calls.append((tuple(targets), as_json))
        return "REPORT", [{"label": "demo", "count": 0, "exists": True}]

    monkeypatch.setattr(auto_debug.auto_report, "render_report", fake_render)

    def fail_once(cmd, env):
        return 1

    ctx = auto_debug.ReportContext.build(
        targets=[("demo", Path("foo.jsonl"))],
        as_json=True,
        snapshot_path=None,
        diff_path=None,
    )
    rc = auto_debug.run_cycle(
        pytest_args=[],
        domains=["all"],
        max_cycles=1,
        skip_auto_evolve=True,
        keep_memory=False,
        report_context=ctx,
        runner=fail_once,
    )
    assert rc == 1
    assert report_calls[0][1] is True


def test_auto_debug_report_context_handles_snapshot_and_diff(monkeypatch, tmp_path):
    snapshot_calls = []
    diff_calls = []

    def fake_render(root, targets, as_json):
        return "TXT", [{"label": "demo", "count": 1, "exists": True}]

    def fake_write(path, payload):
        snapshot_calls.append((path, payload))

    def fake_load(path):
        return [{"label": "demo", "count": 0, "exists": True}] if path else None

    def fake_diff(curr, prev):
        diff_calls.append((curr, prev))
        return "DIFF"

    monkeypatch.setattr(auto_debug.auto_report, "render_report", fake_render)
    monkeypatch.setattr(auto_debug.auto_report, "write_snapshot", fake_write)
    monkeypatch.setattr(auto_debug.auto_report, "load_snapshot", fake_load)
    monkeypatch.setattr(auto_debug.auto_report, "format_diff", fake_diff)

    ctx = auto_debug.ReportContext.build(
        targets=[("demo", Path("foo.jsonl"))],
        as_json=False,
        snapshot_path=str(tmp_path / "snap.json"),
        diff_path=str(tmp_path / "snap.json"),
    )
    assert ctx is not None

    def always_fail(cmd, env):
        return 1

    rc = auto_debug.run_cycle(
        pytest_args=[],
        domains=["all"],
        max_cycles=1,
        skip_auto_evolve=True,
        keep_memory=False,
        report_context=ctx,
        runner=always_fail,
    )
    assert rc == 1
    assert snapshot_calls
    assert diff_calls


def test_auto_debug_focus_emits_suggestions(monkeypatch, capsys):
    payload = [{"label": "semantic"}]

    class DummyReport:
        def __init__(self):
            self.calls = 0

        def emit(self):
            self.calls += 1
            return payload

    dummy_context = DummyReport()

    def fake_select(entries, mapping):
        assert entries == payload
        return {"tests/nsr/test_meta_*"}, set()

    def fake_render(selected, unknown):
        assert selected == ["tests/nsr/test_meta_*"]
        assert unknown == []
        return "FOCUS"

    monkeypatch.setattr(auto_debug.auto_focus, "select_targets", fake_select)
    monkeypatch.setattr(auto_debug.auto_focus, "render_text", fake_render)

    focus = auto_debug.FocusConfig(fmt="text", base_command="pytest", mapping={"semantic": ["tests"]})

    def always_fail(cmd, env):
        return 1

    rc = auto_debug.run_cycle(
        pytest_args=[],
        domains=["all"],
        max_cycles=1,
        skip_auto_evolve=True,
        keep_memory=False,
        report_context=dummy_context,
        focus_config=focus,
        runner=always_fail,
    )
    assert rc == 1
    output = capsys.readouterr().out
    assert "focus suggestions" in output
    assert "FOCUS" in output
