"""Summarize mismatch logs to accelerate auto-debug/auto-heal workflows."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
import time
from pathlib import Path
from typing import Iterable, List, Sequence


DEFAULT_TARGETS = (
    ("semantic", Path("logs/semantic_mismatches.jsonl")),
    ("rule", Path("logs/rule_mismatches.jsonl")),
    ("meta_calculus", Path(".meta/meta_calculus_mismatches.jsonl")),
)


@dataclass
class FileSummary:
    label: str
    path: Path
    exists: bool
    count: int
    last_entry: dict | None


def summarize_file(label: str, path: Path) -> FileSummary:
    if not path.exists():
        return FileSummary(label=label, path=path, exists=False, count=0, last_entry=None)
    count = 0
    last_entry: dict | None = None
    try:
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                count += 1
                try:
                    last_entry = json.loads(line)
                except json.JSONDecodeError:
                    last_entry = {"raw": line}
    except OSError:
        return FileSummary(label=label, path=path, exists=False, count=0, last_entry=None)
    return FileSummary(label=label, path=path, exists=True, count=count, last_entry=last_entry)


def build_report(root: Path, targets: Sequence[tuple[str, Path]]) -> list[FileSummary]:
    summaries: list[FileSummary] = []
    for label, rel_path in targets:
        summaries.append(summarize_file(label, (root / rel_path).resolve()))
    return summaries


def format_report(entries: Sequence[FileSummary], as_json: bool) -> str:
    if as_json:
        payload = [
            {
                "label": entry.label,
                "path": str(entry.path),
                "exists": entry.exists,
                "count": entry.count,
                "last_entry": entry.last_entry,
            }
            for entry in entries
        ]
        return json.dumps(payload, ensure_ascii=False, indent=2)
    lines: list[str] = []
    for entry in entries:
        status = "missing" if not entry.exists else "ok"
        lines.append(f"[{entry.label}] {status} :: {entry.count} registros :: {entry.path}")
        if entry.last_entry:
            preview = json.dumps(entry.last_entry, ensure_ascii=False)[:240]
            lines.append(f"  ↳ última entrada: {preview}")
    return "\n".join(lines)


def render_report(
    root: Path,
    targets: Sequence[tuple[str, Path]],
    *,
    as_json: bool,
) -> str:
    summaries = build_report(root, targets)
    return format_report(summaries, as_json=as_json)


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="nucleo-auto-report",
        description="Resume arquivos de mismatches/auto-evolução para agilizar depuração.",
    )
    parser.add_argument(
        "--root",
        default=".",
        help="Diretório raiz analisado (default: %(default)s).",
    )
    parser.add_argument(
        "--paths",
        nargs="*",
        help="Lista personalizada de arquivos JSONL para resumir.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emite o relatório em JSON estruturado.",
    )
    parser.add_argument(
        "--watch",
        type=float,
        default=0.0,
        help="Quando >0, reexecuta o relatório a cada N segundos até Ctrl+C.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    root = Path(args.root).resolve()
    if args.paths:
        targets = [(Path(p).stem or f"target_{idx}", Path(p)) for idx, p in enumerate(args.paths)]
    else:
        targets = DEFAULT_TARGETS
    watch_interval = max(0.0, float(args.watch or 0.0))
    try:
        while True:
            print(render_report(root, targets, as_json=args.json))
            if watch_interval <= 0.0:
                break
            time.sleep(watch_interval)
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
