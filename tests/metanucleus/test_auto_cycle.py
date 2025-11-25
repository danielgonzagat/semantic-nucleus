from metanucleus.cli import auto_cycle


class SpyRunner:
    def __init__(self, codes):
        self.codes = list(codes)
        self.commands = []

    def __call__(self, cmd):
        self.commands.append(cmd)
        return self.codes.pop(0) if self.codes else 0


def test_auto_cycle_runs_all_steps(monkeypatch):
    spy = SpyRunner([0, 0, 0])
    monkeypatch.setattr(auto_cycle, "_run", spy)
    args = [
        "--pytest-args",
        "-k runtime",
        "--report",
        "--post-report",
        "--post-report-json",
        "--post-report-glob",
        "logs/*.jsonl",
        "--prune-glob",
        "logs/*.jsonl",
        "--prune-max-entries",
        "10",
    ]
    rc = auto_cycle.main(args)
    assert rc == 0
    assert spy.commands[0][:2] == ["nucleo-auto-debug", "--pytest-args"]
    assert spy.commands[1][0] == "nucleo-auto-report"
    assert spy.commands[2][0] == "nucleo-auto-prune"


def test_auto_cycle_skips_prune_when_configured(monkeypatch):
    spy = SpyRunner([0, 0])
    monkeypatch.setattr(auto_cycle, "_run", spy)
    rc = auto_cycle.main(["--post-report", "--skip-prune"])
    assert rc == 0
    assert all(cmd[0] != "nucleo-auto-prune" for cmd in spy.commands)


def test_auto_cycle_prunes_on_failure_when_requested(monkeypatch):
    spy = SpyRunner([1, 0, 0])
    monkeypatch.setattr(auto_cycle, "_run", spy)
    rc = auto_cycle.main(["--post-report", "--prune-on-fail"])
    assert rc == 1
    assert any(cmd[0] == "nucleo-auto-prune" for cmd in spy.commands)


def test_auto_cycle_focus_only_enables_auto_debug_flag(monkeypatch):
    spy = SpyRunner([0, 0])
    monkeypatch.setattr(auto_cycle, "_run", spy)
    rc = auto_cycle.main(["--focus", "--skip-prune"])
    assert rc == 0
    debug_cmd = spy.commands[0]
    assert "nucleo-auto-debug" == debug_cmd[0]
    assert "--focus" in debug_cmd
    assert "--report-snapshot" in debug_cmd
    snap_idx = debug_cmd.index("--report-snapshot")
    assert debug_cmd[snap_idx + 1] == "ci-artifacts/auto-report.json"
    assert all(cmd[0] != "nucleo-auto-focus" for cmd in spy.commands)


def test_auto_cycle_runs_post_focus_step(monkeypatch):
    spy = SpyRunner([0, 0, 0])
    monkeypatch.setattr(auto_cycle, "_run", spy)
    rc = auto_cycle.main(
        [
            "--post-focus",
            "--report-snapshot",
            "reports/latest.json",
            "--focus-format",
            "command",
            "--focus-base-command",
            "python -m pytest",
        ]
    )
    assert rc == 0
    debug_cmd = spy.commands[0]
    assert "--focus" in debug_cmd
    focus_cmd = next(cmd for cmd in spy.commands if cmd[0] == "nucleo-auto-focus")
    assert "--report" in focus_cmd
    assert "reports/latest.json" in focus_cmd
    assert "--format" in focus_cmd
    assert "--base-command" in focus_cmd


def test_auto_cycle_focus_rerun_executes_pytest(monkeypatch):
    spy = SpyRunner([0, 0])
    monkeypatch.setattr(auto_cycle, "_run", spy)

    def fake_load(path):
        assert str(path) == "ci-artifacts/auto-report.json"
        return [{"label": "semantic"}]

    def fake_select(entries, mapping):
        assert entries == [{"label": "semantic"}]
        return {"tests/nsr/test_meta_*"}, set()

    monkeypatch.setattr(auto_cycle.auto_focus, "load_entries", fake_load)
    monkeypatch.setattr(auto_cycle.auto_focus, "select_targets", fake_select)
    monkeypatch.setattr(
        auto_cycle.auto_focus,
        "load_mapping",
        lambda path, mode: {"semantic": ["tests/nsr/test_meta_*"]},
    )

    rc = auto_cycle.main(["--focus-rerun", "--skip-prune"])
    assert rc == 0
    rerun_cmd = spy.commands[-1]
    assert rerun_cmd[0] == "pytest"
    assert "tests/nsr/test_meta_*" in rerun_cmd


def test_auto_cycle_focus_propagates_config(monkeypatch):
    spy = SpyRunner([0, 0, 0])
    monkeypatch.setattr(auto_cycle, "_run", spy)
    rc = auto_cycle.main(
        [
            "--focus",
            "--post-focus",
            "--focus-config",
            "focus-map.json",
            "--focus-config-mode",
            "replace",
            "--skip-prune",
        ]
    )
    assert rc == 0
    debug_cmd = spy.commands[0]
    assert "--focus-config" in debug_cmd
    assert "--focus-config-mode" in debug_cmd
    focus_cmd = next(cmd for cmd in spy.commands if cmd[0] == "nucleo-auto-focus")
    assert "--config" in focus_cmd
    assert "--config-mode" in focus_cmd
