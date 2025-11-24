from __future__ import annotations

import json
from pathlib import Path

import pytest

from metanucleus.cli import auto_focus


def write_report(path: Path, entries: list[dict]) -> None:
    path.write_text(json.dumps(entries), encoding="utf-8")


def test_select_targets_maps_known_labels() -> None:
    entries = [{"label": "semantic"}, {"label": "rule"}]
    selected, unknown = auto_focus.select_targets(entries, auto_focus.CATEGORY_TESTS)
    assert "tests/nsr/test_meta_*" in selected
    assert "tests/test_evolution_rules_smoke.py" in selected
    assert not unknown


def test_select_targets_records_unknown_labels() -> None:
    entries = [{"label": "quantum"}, {"label": "meta_calculus"}]
    selected, unknown = auto_focus.select_targets(entries, auto_focus.CATEGORY_TESTS)
    assert "tests/test_meta_calculus_smoke.py" in selected
    assert unknown == {"quantum"}


def test_cli_text_output(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    report = tmp_path / "report.json"
    write_report(report, [{"label": "semantic"}])
    rc = auto_focus.main(["--report", str(report), "--format", "text"])
    assert rc == 0
    output = capsys.readouterr().out
    assert "tests/nsr/test_meta_*" in output


def test_cli_command_format(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    report = tmp_path / "report.json"
    write_report(report, [{"label": "rule"}])
    rc = auto_focus.main(
        ["--report", str(report), "--format", "command", "--base-command", "python -m pytest"]
    )
    assert rc == 0
    output = capsys.readouterr().out.strip()
    assert output.startswith("python -m pytest")
    assert "tests/test_evolution_rules_smoke.py" in output
