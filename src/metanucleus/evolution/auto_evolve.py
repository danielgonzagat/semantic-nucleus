"""
Orquestra um ciclo completo de autoevolução: pytest → patches → git/PR.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

from metanucleus.kernel.meta_kernel import MetaKernel
from metanucleus.evolution.types import EvolutionPatch
from metanucleus.utils.project import get_project_root

PROJECT_ROOT = get_project_root(Path(__file__))
LOG_PATH = PROJECT_ROOT / ".metanucleus" / "auto_evolve_last.log"


def _run_command(cmd: List[str], *, capture: bool = False, check: bool = True) -> subprocess.CompletedProcess:
    kwargs = {
        "cwd": str(PROJECT_ROOT),
        "text": True,
        "check": check,
    }
    if capture:
        kwargs["capture_output"] = True
    print(f"[auto-evolve] $ {' '.join(cmd)}")
    return subprocess.run(cmd, **kwargs)


def _git_status_porcelain() -> str:
    proc = _run_command(["git", "status", "--porcelain"], capture=True)
    return proc.stdout.strip()


def _git_add_all() -> None:
    _run_command(["git", "add", "-A"])


def _git_commit(message: str) -> None:
    _run_command(["git", "commit", "-m", message], check=False)


def _git_checkout_branch(branch: str) -> None:
    _run_command(["git", "checkout", "-b", branch], check=False)


def _git_push(branch: str) -> None:
    _run_command(["git", "push", "origin", branch], check=False)


def run_pytest(args: Optional[List[str]] = None, skip: bool = False) -> Optional[int]:
    if skip:
        print("[auto-evolve] pytest skipped by flag.")
        return None
    cmd = [sys.executable, "-m", "pytest"]
    if args:
        cmd.extend(args)
    result = _run_command(cmd, check=False)
    print(f"[auto-evolve] pytest exit code: {result.returncode}")
    return result.returncode


def run_auto_patches(
    domains: Iterable[str],
    *,
    max_patches: Optional[int],
    apply_changes: bool,
    source: str,
) -> Tuple[List[EvolutionPatch], List[Dict[str, str]]]:
    kernel = MetaKernel()
    patches = kernel.run_auto_evolution_cycle(
        domains=domains,
        max_patches=max_patches,
        apply_changes=apply_changes,
        source=source,
    )
    stats = getattr(kernel, "last_evolution_stats", [])
    return patches, stats


def log_summary(patches: List[EvolutionPatch], pytest_code: Optional[int], branch: Optional[str]) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    LOG_PATH.write_text(
        f"time: {timestamp}\n"
        f"pytest_code: {pytest_code}\n"
        f"patches: {[p.domain for p in patches]}\n"
        f"branch: {branch or '-'}\n",
        encoding="utf-8",
    )


@dataclass
class Arguments:
    domains: List[str]
    max_patches: Optional[int]
    skip_tests: bool
    pytest_args: Optional[List[str]]
    dry_run: bool
    source: str
    commit: bool
    push: bool
    branch_prefix: str
    commit_message: Optional[str]


def parse_args(argv: Optional[List[str]] = None) -> Arguments:
    parser = argparse.ArgumentParser(
        prog="metanucleus-auto-evolve",
        description="Pytest → auto-patches → (opcional) branch/commit/push automático.",
    )
    parser.add_argument(
        "domains",
        nargs="*",
        default=["all"],
        help="Domínios para evoluir (intent, rules, semantics, semantic_frames, meta_calculus, all).",
    )
    parser.add_argument("--max-patches", type=int, default=None, help="Limita o número de patches aplicados.")
    parser.add_argument("--skip-tests", action="store_true", help="Não roda pytest antes do ciclo.")
    parser.add_argument("--pytest-args", nargs="*", default=None, help="Argumentos extras para pytest.")
    parser.add_argument("--dry-run", action="store_true", help="Não aplica diffs; só mostra os patches.")
    parser.add_argument("--source", default="cli-auto-evolve", help="Identificador de origem registrado no patch.")
    parser.add_argument("--commit", action="store_true", help="Cria branch/commit automaticamente quando houver mudanças.")
    parser.add_argument("--push", action="store_true", help="Se combinado com --commit, faz git push origin <branch>.")
    parser.add_argument("--branch-prefix", default="auto-evolve", help="Prefixo para a branch automática (default: auto-evolve).")
    parser.add_argument("--commit-message", default=None, help="Mensagem customizada para o commit.")

    args_ns = parser.parse_args(argv)
    return Arguments(
        domains=list(args_ns.domains),
        max_patches=args_ns.max_patches,
        skip_tests=args_ns.skip_tests,
        pytest_args=args_ns.pytest_args,
        dry_run=args_ns.dry_run,
        source=args_ns.source,
        commit=args_ns.commit,
        push=args_ns.push,
        branch_prefix=args_ns.branch_prefix,
        commit_message=args_ns.commit_message,
    )


def main(argv: Optional[List[str]] = None) -> None:
    args = parse_args(argv)

    pytest_code = run_pytest(args.pytest_args, skip=args.skip_tests)
    patches, stats = run_auto_patches(
        args.domains,
        max_patches=args.max_patches,
        apply_changes=not args.dry_run,
        source=args.source,
    )

    if stats:
        print("[auto-evolve] domínios analisados:")
        for entry in stats:
            reason = entry.get("reason")
            suffix = f" ({reason})" if reason else ""
            print(f"  - {entry.get('domain')}: {entry.get('status')}{suffix}")
        print()

    if not patches:
        print("[auto-evolve] nenhum patch foi gerado.")
        log_summary([], pytest_code, None)
        return

    print(f"[auto-evolve] patches gerados: {len(patches)}")

    if args.dry_run:
        print("[auto-evolve] modo dry-run — exibindo diffs:")
        for idx, patch in enumerate(patches, start=1):
            print(f"\n--- PATCH #{idx} [{patch.domain}] {patch.title} ---\n")
            print(patch.diff)
        log_summary(patches, pytest_code, None)
        return

    branch_name = None
    if args.commit and _git_status_porcelain():
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        branch_name = f"{args.branch_prefix}-{timestamp}"
        _git_checkout_branch(branch_name)
        _git_add_all()
        commit_msg = args.commit_message or f"auto-evolve: patches {timestamp}"
        _git_commit(commit_msg)
        if args.push:
            _git_push(branch_name)
        print(f"[auto-evolve] branch criada: {branch_name}")
    elif args.commit:
        print("[auto-evolve] nenhum arquivo mudou após aplicar patches; commit ignorado.")

    log_summary(patches, pytest_code, branch_name)


if __name__ == "__main__":  # pragma: no cover
    main()
