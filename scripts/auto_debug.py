#!/usr/bin/env python3
"""
Orquestra ciclos determinísticos de diagnóstico → auto-correção → verificação.

O fluxo padrão executa:
1. pytest (suíte completa)
2. pytest tests/cts (compatibilidade de protocolos)
3. Validação dos LangPacks (pt/en/es/fr/it)
4. metanucleus-auto-evolve all --skip-tests (aplica patches determinísticos sem repetir pytest)

Se alguma etapa falhar, o pipeline aplica os fixers e repete até atingir
estabilidade ou um limite de ciclos.
"""

from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
import sys
from typing import Iterable, Sequence


@dataclass(slots=True)
class CommandSpec:
    """Comando determinístico a ser executado durante o ciclo."""

    name: str
    argv: Sequence[str]
    critical: bool = True
    env: dict[str, str] | None = None


@dataclass(slots=True)
class CommandResult:
    """Resultado serializável do comando."""

    name: str
    argv: Sequence[str]
    returncode: int
    duration_seconds: float
    stdout: str
    stderr: str

    @property
    def ok(self) -> bool:
        return self.returncode == 0


@dataclass(slots=True)
class CycleReport:
    """Resumo de um ciclo completo (diagnóstico + fix)."""

    index: int
    diagnostics: list[CommandResult] = field(default_factory=list)
    fixes: list[CommandResult] = field(default_factory=list)
    changes_detected: bool = False
    success: bool = False


@dataclass(slots=True)
class PipelineReport:
    """Estrutura serializável do pipeline."""

    success: bool
    cycles: list[CycleReport]

    def to_dict(self) -> dict[str, object]:
        return {
            "success": self.success,
            "cycles": [
                {
                    "index": cycle.index,
                    "changes_detected": cycle.changes_detected,
                    "success": cycle.success,
                    "diagnostics": [asdict(cmd) for cmd in cycle.diagnostics],
                    "fixes": [asdict(cmd) for cmd in cycle.fixes],
                }
                for cycle in self.cycles
            ],
        }


LANGPACK_CODES = ("pt", "en", "es", "fr", "it")
PYTHON_BIN = os.environ.get("PYTHON_EXECUTABLE", sys.executable)

DEFAULT_DIAGNOSTICS: tuple[CommandSpec, ...] = (
    CommandSpec(name="pytest", argv=(PYTHON_BIN, "-m", "pytest")),
    CommandSpec(name="pytest-cts", argv=(PYTHON_BIN, "-m", "pytest", "tests/cts")),
) + tuple(
    CommandSpec(
        name=f"langpack-{code}",
        argv=(
            PYTHON_BIN,
            "scripts/langpack_check.py",
            "--code",
            code,
            "--fail-on-warn",
        ),
        critical=False,
    )
    for code in LANGPACK_CODES
)

DEFAULT_FIXERS: tuple[CommandSpec, ...] = (
    CommandSpec(
        name="metanucleus-auto-evolve",
        argv=("metanucleus-auto-evolve", "all", "--skip-tests"),
        critical=False,
    ),
)


class AutoDebugPipeline:
    """Executa ciclos até todos os diagnósticos passarem ou o limite estourar."""

    def __init__(
        self,
        *,
        repo_root: Path,
        diagnostics: Iterable[CommandSpec],
        fixers: Iterable[CommandSpec],
        max_cycles: int,
        verbose: bool,
    ) -> None:
        self.repo_root = repo_root
        self.diagnostics = tuple(diagnostics)
        self.fixers = tuple(fixers)
        self.max_cycles = max_cycles
        self.verbose = verbose

    def run(self) -> PipelineReport:
        cycles: list[CycleReport] = []
        for idx in range(1, self.max_cycles + 1):
            cycle = CycleReport(index=idx)
            if self.verbose:
                print(f"==> Ciclo #{idx} — diagnósticos")
            cycle.diagnostics = [self._run_command(spec) for spec in self.diagnostics]
            diagnostics_ok = all(
                result.ok
                for result in cycle.diagnostics
                if spec_is_critical(result, self.diagnostics)
            )
            if diagnostics_ok:
                cycle.success = True
                cycles.append(cycle)
                return PipelineReport(success=True, cycles=cycles)

            git_before = git_status(self.repo_root)
            if self.verbose:
                print(f"==> Ciclo #{idx} — auto-correções determinísticas")
            cycle.fixes = [self._run_command(spec) for spec in self.fixers]
            git_after = git_status(self.repo_root)
            cycle.changes_detected = git_before != git_after
            cycles.append(cycle)

            if not cycle.changes_detected:
                if self.verbose:
                    print("Nenhuma alteração detectada após os fixers; encerrando.")
                break

        return PipelineReport(success=False, cycles=cycles)

    def _run_command(self, spec: CommandSpec) -> CommandResult:
        start = time.perf_counter()
        env = os.environ.copy()
        env["PATH"] = _ensure_local_bin(env.get("PATH", ""))
        env.setdefault("PYTHON_EXECUTABLE", PYTHON_BIN)
        if spec.env:
            env.update(spec.env)
        try:
            proc = subprocess.run(
                spec.argv,
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                env=env,
                check=False,
            )
            duration = time.perf_counter() - start
            if self.verbose or proc.returncode != 0:
                print(f"[{spec.name}] exit={proc.returncode} time={duration:.2f}s")
                if proc.stdout:
                    print(proc.stdout)
                if proc.stderr:
                    print(proc.stderr)
            return CommandResult(
                name=spec.name,
                argv=spec.argv,
                returncode=proc.returncode,
                duration_seconds=duration,
                stdout=proc.stdout,
                stderr=proc.stderr,
            )
        except FileNotFoundError:
            duration = time.perf_counter() - start
            message = f"Comando não encontrado: {spec.argv[0]}"
            print(f"[{spec.name}] {message}")
            return CommandResult(
                name=spec.name,
                argv=spec.argv,
                returncode=127,
                duration_seconds=duration,
                stdout="",
                stderr=message,
            )


def spec_is_critical(result: CommandResult, specs: Sequence[CommandSpec]) -> bool:
    """Determina se o comando era crítico na configuração original."""
    for spec in specs:
        if spec.name == result.name:
            return spec.critical
    return True


def git_status(repo_root: Path) -> str:
    """Retorna a saída normalizada do git status --porcelain."""
    proc = subprocess.run(
        ("git", "status", "--porcelain"),
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    return proc.stdout.strip()


def _ensure_local_bin(path_value: str) -> str:
    """Garante que ~/.local/bin esteja no PATH para comandos instalados via pip --user."""
    local_bin = str(Path.home() / ".local" / "bin")
    parts = path_value.split(os.pathsep) if path_value else []
    if local_bin not in parts:
        parts.append(local_bin)
    return os.pathsep.join(part for part in parts if part)


def parse_custom_command(raw: str) -> CommandSpec:
    """
    Converte strings do tipo "nome:cmd ..." em CommandSpec.
    Exemplo: --diagnostic "mypy:mypy src"
    """
    if ":" not in raw:
        raise argparse.ArgumentTypeError("Use formato nome:comando")
    name, command = raw.split(":", 1)
    argv = tuple(shlex.split(command))
    if not argv:
        raise argparse.ArgumentTypeError("Comando vazio")
    return CommandSpec(name=name.strip(), argv=argv)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Pipeline determinístico de auto-debug."
    )
    parser.add_argument(
        "--max-cycles",
        type=int,
        default=3,
        help="Quantidade máxima de ciclos diagnóstico→fix (default: 3).",
    )
    parser.add_argument(
        "--diagnostic",
        action="append",
        type=parse_custom_command,
        help="Adiciona comando de diagnóstico extra (formato nome:cmd ...). Pode repetir.",
    )
    parser.add_argument(
        "--fix",
        action="append",
        type=parse_custom_command,
        help="Adiciona comando de auto-correção extra (formato nome:cmd ...). Pode repetir.",
    )
    parser.add_argument(
        "--report",
        type=Path,
        help="Arquivo JSON para salvar o relatório completo do pipeline.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Imprime stdout/stderr completo durante a execução.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    repo_root = Path(__file__).resolve().parents[1]

    diagnostics: tuple[CommandSpec, ...]
    if args.diagnostic:
        diagnostics = DEFAULT_DIAGNOSTICS + tuple(args.diagnostic)
    else:
        diagnostics = DEFAULT_DIAGNOSTICS

    fixers: tuple[CommandSpec, ...]
    if args.fix:
        fixers = DEFAULT_FIXERS + tuple(args.fix)
    else:
        fixers = DEFAULT_FIXERS

    pipeline = AutoDebugPipeline(
        repo_root=repo_root,
        diagnostics=diagnostics,
        fixers=fixers,
        max_cycles=max(1, args.max_cycles),
        verbose=bool(args.verbose),
    )
    report = pipeline.run()
    if args.report:
        args.report.write_text(json.dumps(report.to_dict(), indent=2), encoding="utf-8")
        print(f"Relatório salvo em {args.report}")
    return 0 if report.success else 1


if __name__ == "__main__":
    raise SystemExit(main())
