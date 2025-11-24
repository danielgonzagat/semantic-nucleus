import json
from pathlib import Path

from metanucleus.cli import auto_report


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row) + "\n")


def test_summarize_file_counts_and_last_entry(tmp_path: Path):
    file_path = tmp_path / "semantic.jsonl"
    payload = [{"id": 1, "msg": "a"}, {"id": 2, "msg": "b"}]
    write_jsonl(file_path, payload)
    summary = auto_report.summarize_file("semantic", file_path)
    assert summary.count == 2
    assert summary.exists is True
    assert summary.last_entry == payload[-1]


def test_build_report_uses_defaults(tmp_path: Path):
    write_jsonl(tmp_path / "logs/semantic_mismatches.jsonl", [{"id": 7}])
    summaries = auto_report.build_report(tmp_path, auto_report.DEFAULT_TARGETS)
    labels = {entry.label for entry in summaries}
    assert {"semantic", "rule", "meta_calculus"} == labels
    semantic = next(entry for entry in summaries if entry.label == "semantic")
    assert semantic.count == 1


def test_format_report_json(tmp_path: Path):
    write_jsonl(tmp_path / "file.jsonl", [{"foo": "bar"}])
    summary = auto_report.summarize_file("file", tmp_path / "file.jsonl")
    report = auto_report.format_report([summary], as_json=True)
    data = json.loads(report)
    assert data[0]["label"] == "file"
    assert data[0]["count"] == 1


def test_render_report_returns_string(tmp_path: Path):
    path = tmp_path / "logs/semantic_mismatches.jsonl"
    write_jsonl(path, [{"msg": "ok"}])
    output = auto_report.render_report(
        tmp_path,
        [("demo", Path("logs/semantic_mismatches.jsonl"))],
        as_json=False,
    )
    assert "[demo]" in output


def test_resolve_targets_supports_glob(tmp_path: Path):
    write_jsonl(tmp_path / "logs/a.jsonl", [{"a": 1}])
    write_jsonl(tmp_path / "logs/b.jsonl", [{"b": 2}])
    targets = auto_report.resolve_targets(
        tmp_path,
        path_args=None,
        glob_args=["logs/*.jsonl"],
    )
    labels = {label for label, _ in targets}
    assert "logs/a.jsonl" in labels
    assert "logs/b.jsonl" in labels
