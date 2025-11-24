"""Utilities to prune mismatch logs and keep auto-debug pipelines clean."""

from __future__ import annotations

import argparse
import datetime as dt
from pathlib import Path
from typing import Iterable, List, Sequence

from . import auto_report

DEFAULT_MAX_ENTRIES = 200


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="nucleo-auto-prune",
        description="Remove registros antigos de logs JSONL de mismatch, mantendo apenas os mais recentes.",
    )
    parser.add_argument(
        "--root",
        default=".",
        help="Diretório raiz analisado (default: %(default)s).",
    )
    parser.add_argument(
        "--paths",
        nargs="*",
        help="Arquivos JSONL específicos para podar (pode repetir).",
    )
    parser.add_argument(
        "--glob",
        action="append",
        dest="glob_patterns",
        help="Pattern (relativo ao root) para selecionar múltiplos arquivos.",
    )
    parser.add_argument(
        "--max-entries",
        type=int,
        default=DEFAULT_MAX_ENTRIES,
        help="Quantidade máxima de entradas por arquivo após a poda (default: %(default)s).",
    )
    parser.add_argument(
        "--archive-dir",
        help="Diretório opcional para onde as entradas removidas serão salvas.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Mostra o que seria removido sem alterar os arquivos.",
    )
    return parser.parse_args(argv)


def _glob_targets(root: Path, patterns: Iterable[str]) -> list[Path]:
    targets: list[Path] = []
    for pattern in patterns:
        targets.extend(sorted(p for p in root.glob(pattern) if p.is_file()))
    return targets


def _gather_files(root: Path, paths: Sequence[str] | None, glob_patterns: Sequence[str] | None) -> list[Path]:
    files: list[Path] = []
    if paths:
        files.extend((root / path).resolve() for path in paths)
    if glob_patterns:
        files.extend(_glob_targets(root, glob_patterns))
    if not files:
        files = [(root / rel_path).resolve() for _, rel_path in auto_report.DEFAULT_TARGETS]
    # Remove duplicates preserving order
    seen: set[Path] = set()
    ordered: list[Path] = []
    for path in files:
        if path not in seen:
            ordered.append(path)
            seen.add(path)
    return ordered


def _archive_path(archive_dir: Path, source: Path) -> Path:
    timestamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d%H%M%S")
    archive_dir.mkdir(parents=True, exist_ok=True)
    target_name = f"{source.stem}.{timestamp}.jsonl"
    return archive_dir / target_name


def _prune_file(
    path: Path,
    *,
    max_entries: int,
    archive_dir: Path | None,
    dry_run: bool,
) -> tuple[int, int]:
    if max_entries <= 0 or not path.exists():
        return 0, 0
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return 0, 0
    total = len(lines)
    if total <= max_entries:
        return total, 0
    to_remove = total - max_entries
    removed_lines = lines[:to_remove]
    remaining_lines = lines[to_remove:]
    if archive_dir and removed_lines:
        archive_path = _archive_path(archive_dir, path)
        archive_path.write_text("\n".join(removed_lines) + ("\n" if removed_lines else ""), encoding="utf-8")
    if not dry_run:
        path.write_text("\n".join(remaining_lines) + ("\n" if remaining_lines else ""), encoding="utf-8")
    return total, to_remove


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    root = Path(args.root).resolve()
    max_entries = max(1, int(args.max_entries))
    files = _gather_files(root, args.paths, args.glob_patterns)
    archive_dir = Path(args.archive_dir).resolve() if args.archive_dir else None
    summary: list[str] = []
    for file_path in files:
        total, removed = _prune_file(
            file_path,
            max_entries=max_entries,
            archive_dir=archive_dir,
            dry_run=args.dry_run,
        )
        if total == 0:
            summary.append(f"[skip] {file_path} (sem entradas ou inacessível)")
        elif removed == 0:
            summary.append(f"[ok] {file_path} já possui <= {max_entries} entradas ({total}).")
        else:
            action = "would remove" if args.dry_run else "removed"
            summary.append(
                f"[{action}] {removed} entradas antigas de {file_path} (total antes: {total}, mantendo {max_entries})."
            )
    print("\n".join(summary))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
