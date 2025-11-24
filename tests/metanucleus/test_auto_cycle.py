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
