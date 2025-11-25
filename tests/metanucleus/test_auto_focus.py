from __future__ import annotations

import json
from pathlib import Path

import pytest

from metanucleus.cli import auto_focus


def write_report(path: Path, entries: list[dict]) -> None:
    path.write_text(json.dumps(entries), encoding="utf-8")


def test_select_targets_maps_known_labels() -> None:
    entries = [{"label": "semantic"}, {"label": "rule"}]
    selected, unknown = auto_focus.select_targets(entries, auto_focus.DEFAULT_CATEGORY_TESTS)
    assert "tests/nsr/test_meta_*" in selected
    assert "tests/test_evolution_rules_smoke.py" in selected
    assert not unknown


def test_select_targets_records_unknown_labels() -> None:
    entries = [{"label": "quantum"}, {"label": "meta_calculus"}]
    selected, unknown = auto_focus.select_targets(entries, auto_focus.DEFAULT_CATEGORY_TESTS)
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


def test_load_mapping_merge_and_replace(tmp_path: Path) -> None:
    cfg = tmp_path / "focus.json"
    cfg.write_text(json.dumps({"semantic": ["custom/tests.py"], "extra": "tests/foo.py"}), encoding="utf-8")
    merged = auto_focus.load_mapping(cfg, mode="merge")
    assert merged["semantic"] == ["custom/tests.py"]
    assert merged["extra"] == ["tests/foo.py"]
    assert "rule" in merged  # default preserved
    replaced = auto_focus.load_mapping(cfg, mode="replace")
    assert "rule" not in replaced
    assert replaced["semantic"] == ["custom/tests.py"]


def test_cli_respects_custom_mapping(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    report = tmp_path / "report.json"
    cfg = tmp_path / "focus.json"
    write_report(report, [{"label": "custom"}])
    cfg.write_text(json.dumps({"custom": ["tests/custom_suite.py"]}), encoding="utf-8")
    rc = auto_focus.main(
        ["--report", str(report), "--format", "text", "--config", str(cfg), "--config-mode", "replace"]
    )
    assert rc == 0
    output = capsys.readouterr().out
    assert "tests/custom_suite.py" in output


def test_resolve_config_env(monkeypatch, tmp_path: Path) -> None:
    cfg = tmp_path / "foo.json"
    cfg.write_text("{}", encoding="utf-8")
    monkeypatch.setenv(auto_focus.CONFIG_ENV_VAR, str(cfg))
    resolved = auto_focus.resolve_config_path(None)
    assert resolved == cfg.resolve()


def test_resolve_config_default_file(monkeypatch, tmp_path: Path) -> None:
    focus_dir = tmp_path / "ci"
    focus_dir.mkdir()
    cfg = focus_dir / "focus-map.json"
    cfg.write_text("{}", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    resolved = auto_focus.resolve_config_path(None)
    assert resolved == cfg.resolve()
