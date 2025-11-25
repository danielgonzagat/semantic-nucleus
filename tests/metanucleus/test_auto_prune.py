import json
from pathlib import Path

from metanucleus.cli import auto_prune, auto_report


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row) + "\n")


def read_lines(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8").splitlines()


def test_prune_file_truncates_and_archives(tmp_path: Path, monkeypatch):
    target = tmp_path / "semantic_mismatches.jsonl"
    rows = [{"id": idx} for idx in range(5)]
    write_jsonl(target, rows)
    archive_dir = tmp_path / "archive"
    total, removed = auto_prune._prune_file(
        target,
        max_entries=3,
        archive_dir=archive_dir,
        dry_run=False,
    )
    assert total == 5
    assert removed == 2
    assert len(read_lines(target)) == 3
    archived_files = list(archive_dir.glob("semantic_mismatches*.jsonl"))
    assert archived_files
    archived_lines = read_lines(archived_files[0])
    assert len(archived_lines) == 2


def test_prune_file_dry_run(tmp_path: Path):
    target = tmp_path / "rule_mismatches.jsonl"
    rows = [{"id": idx} for idx in range(4)]
    write_jsonl(target, rows)
    total, removed = auto_prune._prune_file(
        target,
        max_entries=2,
        archive_dir=None,
        dry_run=True,
    )
    assert total == 4
    assert removed == 2
    assert len(read_lines(target)) == 4


def test_gather_files_defaults_to_auto_report(tmp_path: Path):
    files = auto_prune._gather_files(tmp_path, paths=None, glob_patterns=None)
    # Default paths relative to root
    expected = [(tmp_path / rel).resolve() for _, rel in auto_report.DEFAULT_TARGETS]
    assert files == expected
