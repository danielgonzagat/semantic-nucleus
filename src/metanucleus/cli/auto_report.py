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


def summaries_to_payload(entries: Sequence[FileSummary]) -> list[dict]:
    return [
        {
            "label": entry.label,
            "path": str(entry.path),
            "exists": entry.exists,
            "count": entry.count,
            "last_entry": entry.last_entry,
        }
        for entry in entries
    ]


def format_payload(payload: Sequence[dict], as_json: bool) -> str:
    if as_json:
        return json.dumps(payload, ensure_ascii=False, indent=2)
    lines: list[str] = []
    for entry in payload:
        status = "missing" if not entry.get("exists") else "ok"
        lines.append(
            f"[{entry.get('label')}] {status} :: {entry.get('count', 0)} registros :: {entry.get('path')}"
        )
        last_entry = entry.get("last_entry")
        if last_entry:
            preview = json.dumps(last_entry, ensure_ascii=False)[:240]
            lines.append(f"  ↳ última entrada: {preview}")
    return "\n".join(lines)


def format_diff(current: Sequence[dict], previous: Sequence[dict] | None) -> str:
    prev_map = {entry.get("label"): entry for entry in (previous or [])}
    lines: list[str] = []
    for entry in current:
        label = entry.get("label")
        prev = prev_map.pop(label, None)
        prev_count = prev.get("count", 0) if prev else 0
        prev_exists = prev.get("exists") if prev else False
        delta = entry.get("count", 0) - prev_count
        exists_change = ""
        if prev and prev_exists != entry.get("exists"):
            exists_change = f" status {prev_exists}->{entry.get('exists')}"
        if not prev:
            lines.append(f"[{label}] novo arquivo (count={entry.get('count',0)})")
        elif delta or exists_change:
            lines.append(
                f"[{label}] Δcount {delta:+d}{exists_change} (agora {entry.get('count',0)})"
            )
    for label, prev in prev_map.items():
        lines.append(f"[{label}] removido (count anterior {prev.get('count',0)})")
    return "\n".join(lines)


def render_report(
    root: Path,
    targets: Sequence[tuple[str, Path]],
    *,
    as_json: bool,
) -> tuple[str, list[dict]]:
    summaries = build_report(root, targets)
    payload = summaries_to_payload(summaries)
    return format_payload(payload, as_json=as_json), payload


def resolve_targets(
    root: Path,
    path_args: Sequence[str] | None,
    glob_args: Sequence[str] | None,
) -> list[tuple[str, Path]]:
    targets: list[tuple[str, Path]] = []
    if path_args:
        for idx, raw in enumerate(path_args):
            path = (root / raw).resolve()
            label = Path(raw).stem or f"target_{idx+1}"
            targets.append((label, path))
    if glob_args:
        for pattern in glob_args:
            matches = sorted(p for p in root.glob(pattern or "") if p.is_file())
            for match in matches:
                rel = match.relative_to(root)
                targets.append((str(rel), match.resolve()))
    if not targets:
        targets = [(label, (root / rel_path).resolve()) for label, rel_path in DEFAULT_TARGETS]
    return targets


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
        "--glob",
        action="append",
        dest="glob_patterns",
        help="Pattern (relative ao --root) para incluir múltiplos arquivos. Pode repetir.",
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
    parser.add_argument(
        "--snapshot",
        help="Quando informado, grava o relatório atual (JSON) no caminho indicado.",
    )
    parser.add_argument(
        "--diff",
        help="Compara o relatório atual com um snapshot JSON anterior e imprime as diferenças.",
    )
    return parser.parse_args(argv)


def load_snapshot(path: str | None) -> list[dict] | None:
    if not path:
        return None
    snap_path = Path(path)
    if not snap_path.exists():
        return None
    try:
        with snap_path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
            return data if isinstance(data, list) else None
    except (OSError, json.JSONDecodeError):
        return None


def write_snapshot(path: str | None, payload: Sequence[dict]) -> None:
    if not path:
        return
    snap_path = Path(path)
    snap_path.parent.mkdir(parents=True, exist_ok=True)
    snap_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    root = Path(args.root).resolve()
    targets = resolve_targets(root, args.paths, args.glob_patterns)
    watch_interval = max(0.0, float(args.watch or 0.0))
    baseline = load_snapshot(args.diff)
    try:
        while True:
            text, payload = render_report(root, targets, as_json=args.json)
            if baseline:
                diff_text = format_diff(payload, baseline)
                if diff_text:
                    print(diff_text)
            print(text)
            if args.snapshot:
                write_snapshot(args.snapshot, payload)
                baseline = payload if args.diff and args.diff == args.snapshot else baseline
            if watch_interval <= 0.0:
                break
            time.sleep(watch_interval)
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
