"""Utility to run deterministic debug/auto-healing cycles locally or in CI."""

from __future__ import annotations

import argparse
import os
import shlex
import subprocess
import sys
from typing import Iterable, List


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


def run_cycle(
    pytest_args: Iterable[str],
    domains: Iterable[str],
    max_cycles: int,
    *,
    skip_auto_evolve: bool,
    keep_memory: bool,
    runner=_run_command,
) -> int:
    env = _build_env(disable_memory=not keep_memory)
    pytest_cmd = [sys.executable, "-m", "pytest", *pytest_args]
    auto_cmd = ["metanucleus-auto-evolve", *domains, "--apply"]

    max_cycles = max(1, int(max_cycles))
    attempt = 0
    while attempt < max_cycles:
        attempt += 1
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
    return 1


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    pytest_args = shlex.split(args.pytest_args)
    domains = _split_items(args.auto_evolve_domains) or ["all"]
    return run_cycle(
        pytest_args,
        domains,
        args.max_cycles,
        skip_auto_evolve=args.skip_auto_evolve,
        keep_memory=args.keep_memory,
    )


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
