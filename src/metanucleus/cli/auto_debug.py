"""Utility to run deterministic debug/auto-healing cycles locally or in CI."""

from __future__ import annotations

import argparse
import os
import shlex
import subprocess
import sys
from dataclasses import dataclass
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
    parser.add_argument(
        "--report-snapshot",
        help="Quando definido, grava o relatório atual (JSON) no caminho indicado.",
    )
    parser.add_argument(
        "--report-diff",
        help="Compara o relatório atual com um snapshot JSON anterior e imprime o delta.",
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


@dataclass
class ReportContext:
    targets: Sequence[tuple[str, Path]]
    as_json: bool
    root: Path
    snapshot_path: str | None = None
    diff_path: str | None = None
    baseline: list[dict] | None = None

    @classmethod
    def build(
        cls,
        targets: Sequence[tuple[str, Path]] | None,
        *,
        as_json: bool,
        snapshot_path: str | None,
        diff_path: str | None,
    ) -> "ReportContext | None":
        if not targets:
            return None
        root = Path.cwd()
        baseline = auto_report.load_snapshot(diff_path)
        return cls(
            targets=targets,
            as_json=as_json,
            root=root,
            snapshot_path=snapshot_path,
            diff_path=diff_path,
            baseline=baseline,
        )

    def emit(self) -> None:
        text, payload = auto_report.render_report(
            self.root,
            self.targets,
            as_json=self.as_json,
        )
        if self.diff_path:
            diff_text = auto_report.format_diff(payload, self.baseline)
            if diff_text:
                print("[auto-debug] mismatch diff:", flush=True)
                print(diff_text, flush=True)
        print("[auto-debug] mismatch summary:", flush=True)
        print(text, flush=True)
        if self.snapshot_path:
            auto_report.write_snapshot(self.snapshot_path, payload)
            if self.diff_path and self.diff_path == self.snapshot_path:
                self.baseline = payload


def run_cycle(
    pytest_args: Iterable[str],
    domains: Iterable[str],
    max_cycles: int,
    *,
    skip_auto_evolve: bool,
    keep_memory: bool,
    report_context: ReportContext | None = None,
    runner=_run_command,
) -> int:
    env = _build_env(disable_memory=not keep_memory)
    pytest_cmd = [sys.executable, "-m", "pytest", *pytest_args]
    auto_cmd = ["metanucleus-auto-evolve", *domains, "--apply"]

    max_cycles = max(1, int(max_cycles))
    attempt = 0
    while attempt < max_cycles:
        attempt += 1
        if report_context:
            report_context.emit()
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
        if report_context:
            report_context.emit()
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
    report_ctx: ReportContext | None = None
    if args.report or report_targets:
        if not report_targets:
            report_targets = [(label, Path(path)) for label, path in auto_report.DEFAULT_TARGETS]
        report_ctx = ReportContext.build(
            report_targets,
            as_json=args.report_json,
            snapshot_path=args.report_snapshot,
            diff_path=args.report_diff,
        )
    return run_cycle(
        pytest_args,
        domains,
        args.max_cycles,
        skip_auto_evolve=args.skip_auto_evolve,
        keep_memory=args.keep_memory,
        report_context=report_ctx,
    )


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
