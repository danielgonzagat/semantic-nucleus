"""High-level orchestrator: auto-debug → auto-report → auto-prune."""

from __future__ import annotations

import argparse
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Iterable, List


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="nucleo-auto-cycle",
        description="Executa nucleo-auto-debug, nucleo-auto-report e nucleo-auto-prune na sequência.",
    )
    parser.add_argument("--pytest-args", default="", help="Argumentos adicionais para pytest.")
    parser.add_argument(
        "--auto-domains",
        default="all",
        help="Domínios passados ao nucleo-auto-debug (default: %(default)s).",
    )
    parser.add_argument("--max-cycles", type=int, default=3, help="Máximo de tentativas.")
    parser.add_argument("--keep-memory", action="store_true", help="Preserva memória NSR.")
    parser.add_argument("--skip-auto-evolve", action="store_true", help="Não chama metanucleus-auto-evolve.")

    parser.add_argument("--report", action="store_true", help="Ativa relatórios durante o auto-debug.")
    parser.add_argument("--report-json", action="store_true", help="Relatórios em JSON.")
    parser.add_argument("--report-path", action="append", dest="report_paths", help="Arquivos extras para o relatório.")
    parser.add_argument("--report-snapshot", help="Snapshot JSON escrito após o auto-debug.")
    parser.add_argument("--report-diff", help="Snapshot usado como baseline para diff.")
    parser.add_argument(
        "--post-report",
        action="store_true",
        help="Executa nucleo-auto-report após o auto-debug (independente do resultado).",
    )
    parser.add_argument("--post-report-json", action="store_true", help="Post-report em JSON.")
    parser.add_argument("--post-report-glob", action="append", help="Globs adicionais para o post-report.")

    parser.add_argument("--skip-prune", action="store_true", help="Não executa nucleo-auto-prune.")
    parser.add_argument("--prune-on-fail", action="store_true", help="Executa prune mesmo se o auto-debug falhar.")
    parser.add_argument("--prune-path", action="append", dest="prune_paths", help="Arquivos específicos para poda.")
    parser.add_argument("--prune-glob", action="append", dest="prune_globs", help="Globs para poda.")
    parser.add_argument("--prune-max-entries", type=int, default=200, help="Máximo de entradas por arquivo.")
    parser.add_argument("--prune-archive-dir", help="Diretório para salvar entradas removidas.")
    parser.add_argument("--prune-dry-run", action="store_true", help="Não altera arquivos ao podar.")

    parser.add_argument(
        "--focus",
        action="store_true",
        help="Passa --focus para o nucleo-auto-debug e imprime sugestões inline.",
    )
    parser.add_argument(
        "--post-focus",
        action="store_true",
        help="Executa nucleo-auto-focus após o auto-debug (usa snapshots JSON).",
    )
    parser.add_argument(
        "--focus-report",
        help="Snapshot JSON consumido por nucleo-auto-focus (default: --report-snapshot ou ci-artifacts/auto-report.json).",
    )
    parser.add_argument(
        "--focus-format",
        choices=["text", "json", "command"],
        default="text",
        help="Formato de saída do nucleo-auto-focus (default: %(default)s).",
    )
    parser.add_argument(
        "--focus-base-command",
        default="pytest",
        help="Comando base usado quando --focus-format=command (default: %(default)s).",
    )

    return parser.parse_args(argv)


def _split_domains(raw: str) -> List[str]:
    return [token for token in raw.replace(",", " ").split() if token.strip()]


def _run(cmd: List[str]) -> int:
    printable = " ".join(shlex.quote(part) for part in cmd)
    print(f"[auto-cycle] $ {printable}", flush=True)
    proc = subprocess.run(cmd)
    return proc.returncode


def _build_auto_debug_cmd(args: argparse.Namespace) -> List[str]:
    cmd = [
        "nucleo-auto-debug",
        "--pytest-args",
        args.pytest_args,
        "--auto-evolve-domains",
        " ".join(_split_domains(args.auto_domains) or ["all"]),
        "--max-cycles",
        str(max(1, args.max_cycles)),
    ]
    if args.keep_memory:
        cmd.append("--keep-memory")
    if args.skip_auto_evolve:
        cmd.append("--skip-auto-evolve")
    focus_enabled = args.focus or args.post_focus
    if args.report or args.report_paths or args.report_snapshot or args.report_diff or focus_enabled:
        cmd.append("--report")
        if args.report_json:
            cmd.append("--report-json")
        for path in args.report_paths or []:
            cmd.extend(["--report-path", path])
        if args.report_snapshot:
            cmd.extend(["--report-snapshot", args.report_snapshot])
        if args.report_diff:
            cmd.extend(["--report-diff", args.report_diff])
    if focus_enabled:
        cmd.append("--focus")
        cmd.extend(["--focus-format", args.focus_format])
        if args.focus_base_command:
            cmd.extend(["--focus-base-command", args.focus_base_command])
    return cmd


def _build_post_report_cmd(args: argparse.Namespace) -> List[str]:
    cmd = ["nucleo-auto-report"]
    if args.post_report_json:
        cmd.append("--json")
    for glob_pattern in args.post_report_glob or []:
        cmd.extend(["--glob", glob_pattern])
    return cmd


def _build_prune_cmd(args: argparse.Namespace) -> List[str]:
    cmd = [
        "nucleo-auto-prune",
        "--max-entries",
        str(max(1, args.prune_max_entries)),
    ]
    for path in args.prune_paths or []:
        cmd.extend(["--paths", path])
    for pattern in args.prune_globs or []:
        cmd.extend(["--glob", pattern])
    if args.prune_archive_dir:
        cmd.extend(["--archive-dir", args.prune_archive_dir])
    if args.prune_dry_run:
        cmd.append("--dry-run")
    return cmd


def _resolve_focus_report(args: argparse.Namespace) -> str:
    if args.focus_report:
        return args.focus_report
    if args.report_snapshot:
        return args.report_snapshot
    return "ci-artifacts/auto-report.json"


def _build_focus_cmd(args: argparse.Namespace) -> List[str]:
    report_path = _resolve_focus_report(args)
    cmd = [
        "nucleo-auto-focus",
        "--report",
        report_path,
        "--format",
        args.focus_format,
    ]
    if args.focus_format == "command" or args.focus_base_command != "pytest":
        cmd.extend(["--base-command", args.focus_base_command])
    return cmd


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    debug_cmd = _build_auto_debug_cmd(args)
    debug_rc = _run(debug_cmd)

    report_rc = 0
    if args.post_report:
        report_cmd = _build_post_report_cmd(args)
        report_rc = _run(report_cmd)

    focus_rc = 0
    if args.post_focus:
        focus_cmd = _build_focus_cmd(args)
        focus_rc = _run(focus_cmd)

    prune_rc = 0
    should_prune = not args.skip_prune and (debug_rc == 0 or args.prune_on_fail)
    if should_prune:
        prune_cmd = _build_prune_cmd(args)
        prune_rc = _run(prune_cmd)

    return debug_rc or report_rc or focus_rc or prune_rc


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
