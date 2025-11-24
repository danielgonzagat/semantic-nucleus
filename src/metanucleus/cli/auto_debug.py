"""Utility to run deterministic debug/auto-healing cycles locally or in CI."""

from __future__ import annotations

import argparse
import os
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Iterable, List, Sequence

from . import auto_report


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="nucleo-auto-debug",
        description=(
            "Run pytest and, when it fails, trigger metanucleus-auto-evolve before retrying.\n"
            "Useful for automating local debug/auto-healing cycles."
        ),
    )
    parser.add_argument(
        "--pytest-args",
        default="",
        help="Extra arguments passed to pytest (example: \"-k runtime -vv\").",
    )
    parser.add_argument(
        "--auto-evolve-domains",
        default="all",
        help="Space or comma separated list passed to metanucleus-auto-evolve (default: %(default)s).",
    )
    parser.add_argument(
        "--max-cycles",
        type=int,
        default=3,
        help="Maximum number of pytest attempts before giving up (default: %(default)s).",
    )
    parser.add_argument(
        "--skip-auto-evolve",
        action="store_true",
        help="Stop after the first pytest failure without invoking metanucleus-auto-evolve.",
    )
    parser.add_argument(
        "--keep-memory",
        action="store_true",
        help="Keep NSR memory/episodes persistence enabled (disabled by default for determinism).",
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="Imprime um resumo dos arquivos de mismatch antes de cada tentativa.",
    )
    parser.add_argument(
        "--report-json",
        action="store_true",
        help="Formata o relatório em JSON ao usar --report.",
    )
    parser.add_argument(
        "--report-path",
        action="append",
        dest="report_paths",
        help="Arquivo JSONL adicional para aparecer no relatório (pode repetir).",
    )
    return parser.parse_args(argv)


def _split_items(raw: str) -> List[str]:
    tokens = []
    for chunk in raw.replace(",", " ").split():
        if chunk.strip():
            tokens.append(chunk.strip())
    return tokens


def _build_env(disable_memory: bool) -> dict[str, str]:
    env = os.environ.copy()
    if disable_memory:
        env.setdefault("NSR_MEMORY_STORE_PATH", "")
        env.setdefault("NSR_EPISODES_PATH", "")
        env.setdefault("NSR_INDUCTION_RULES_PATH", "")
    return env


def _run_command(cmd: list[str], env: dict[str, str]) -> int:
    printable = " ".join(shlex.quote(part) for part in cmd)
    print(f"[auto-debug] $ {printable}", flush=True)
    result = subprocess.run(cmd, env=env)
    return result.returncode


def _emit_report(
    targets: Sequence[tuple[str, Path]] | None,
    *,
    as_json: bool,
    root: Path | None = None,
) -> None:
    if not targets:
        return
    root = root or Path.cwd()
    text, _payload = auto_report.render_report(root, targets, as_json=as_json)
    print("[auto-debug] mismatch summary:", flush=True)
    print(text, flush=True)


def run_cycle(
    pytest_args: Iterable[str],
    domains: Iterable[str],
    max_cycles: int,
    *,
    skip_auto_evolve: bool,
    keep_memory: bool,
    report_targets: Sequence[tuple[str, Path]] | None = None,
    report_json: bool = False,
    runner=_run_command,
) -> int:
    env = _build_env(disable_memory=not keep_memory)
    pytest_cmd = [sys.executable, "-m", "pytest", *pytest_args]
    auto_cmd = ["metanucleus-auto-evolve", *domains, "--apply"]

    max_cycles = max(1, int(max_cycles))
    attempt = 0
    while attempt < max_cycles:
        attempt += 1
        _emit_report(report_targets, as_json=report_json)
        print(f"[auto-debug] pytest attempt {attempt}/{max_cycles}", flush=True)
        if runner(pytest_cmd, env) == 0:
            print("[auto-debug] pytest succeeded ✅", flush=True)
            return 0
        if skip_auto_evolve or attempt == max_cycles:
            print("[auto-debug] pytest failed and no more retries are allowed.", flush=True)
            return 1
        print("[auto-debug] pytest failed, invoking metanucleus-auto-evolve…", flush=True)
        auto_code = runner(auto_cmd, env)
        if auto_code != 0:
            print("[auto-debug] metanucleus-auto-evolve failed; aborting cycle.", flush=True)
            return auto_code
        _emit_report(report_targets, as_json=report_json)
    return 1


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    pytest_args = shlex.split(args.pytest_args)
    domains = _split_items(args.auto_evolve_domains) or ["all"]
    report_targets: list[tuple[str, Path]] = []
    if args.report_paths:
        for idx, raw in enumerate(args.report_paths):
            path = Path(raw)
            label = path.stem or f"custom_{idx+1}"
            report_targets.append((label, path))
    if args.report or report_targets:
        if not report_targets:
            report_targets = [(label, Path(path)) for label, path in auto_report.DEFAULT_TARGETS]
    else:
        report_targets = None
    return run_cycle(
        pytest_args,
        domains,
        args.max_cycles,
        skip_auto_evolve=args.skip_auto_evolve,
        keep_memory=args.keep_memory,
        report_targets=report_targets,
        report_json=args.report_json,
    )


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
