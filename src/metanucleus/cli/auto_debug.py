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

from . import auto_focus, auto_report


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
    parser.add_argument(
        "--focus",
        action="store_true",
        help="Gera sugestões de pytest com base no relatório atual (implica --report).",
    )
    parser.add_argument(
        "--focus-format",
        choices=["text", "json", "command"],
        default="text",
        help="Formato das sugestões emitidas por --focus (default: %(default)s).",
    )
    parser.add_argument(
        "--focus-base-command",
        default="pytest",
        help="Comando base usado quando --focus-format=command (default: %(default)s).",
    )
    parser.add_argument(
        "--focus-config",
        help="JSON file with label→pytest target mapping para --focus.",
    )
    parser.add_argument(
        "--focus-config-mode",
        choices=["merge", "replace"],
        default="merge",
        help="Como combinar o --focus-config com o mapeamento padrão (default: %(default)s).",
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

    def emit(self) -> list[dict]:
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
        return payload


@dataclass
class FocusConfig:
    fmt: str
    base_command: str
    mapping: dict[str, list[str]]

    def emit(self, payload: Sequence[dict]) -> None:
        selected, unknown = auto_focus.select_targets(payload, self.mapping)
        ordered_selected = sorted(selected)
        ordered_unknown = sorted(unknown)
        if self.fmt == "json":
            text = auto_focus.render_json(ordered_selected, ordered_unknown)
        elif self.fmt == "command":
            text = auto_focus.build_command(ordered_selected, self.base_command)
        else:
            text = auto_focus.render_text(ordered_selected, ordered_unknown)
        print("[auto-debug] focus suggestions:", flush=True)
        print(text, flush=True)


def run_cycle(
    pytest_args: Iterable[str],
    domains: Iterable[str],
    max_cycles: int,
    *,
    skip_auto_evolve: bool,
    keep_memory: bool,
    report_context: ReportContext | None = None,
    focus_config: FocusConfig | None = None,
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
            payload = report_context.emit()
            if focus_config and payload:
                focus_config.emit(payload)
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
            payload = report_context.emit()
            if focus_config and payload:
                focus_config.emit(payload)
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
    if args.focus:
        args.report = True
    report_ctx: ReportContext | None = None
    if args.report or report_targets or args.focus:
        if not report_targets:
            report_targets = [(label, Path(path)) for label, path in auto_report.DEFAULT_TARGETS]
        report_ctx = ReportContext.build(
            report_targets,
            as_json=args.report_json,
            snapshot_path=args.report_snapshot,
            diff_path=args.report_diff,
        )
    focus_config: FocusConfig | None = None
    if args.focus:
        resolved_config = auto_focus.resolve_config_path(args.focus_config)
        try:
            mapping = auto_focus.load_mapping(resolved_config, mode=args.focus_config_mode)
        except ValueError as exc:
            raise SystemExit(f"invalid focus config: {exc}")
        focus_config = FocusConfig(
            fmt=args.focus_format,
            base_command=args.focus_base_command,
            mapping=mapping,
        )
    return run_cycle(
        pytest_args,
        domains,
        args.max_cycles,
        skip_auto_evolve=args.skip_auto_evolve,
        keep_memory=args.keep_memory,
        report_context=report_ctx,
        focus_config=focus_config,
    )


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
