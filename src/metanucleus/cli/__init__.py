"""
Interface de linha de comando para o pipeline de meta-evolução.
"""

from __future__ import annotations

import argparse
import sys
import json
import subprocess
import time
import hashlib
from pathlib import Path
from typing import Iterable, List, Sequence, Tuple

from metanucleus.core.evolution import (
    EvolutionRequest,
    MetaEvolution,
    explanation_to_dict,
)
from metanucleus.core.state import MetaState
from metanucleus.runtime.meta_runtime import MetaRuntime
from metanucleus.runtime.test_suites import get_suite, list_suites
from metanucleus.test.testcore import run_test_suite, TestCase
from metanucleus.utils.suites import load_suite_file, SuiteFormatError


class GitHelperError(RuntimeError):
    """Erro de conveniência para operações git."""


def _run_git(args: Sequence[str]) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(args, check=True, capture_output=True)
    except FileNotFoundError as exc:
        raise GitHelperError("git não encontrado no PATH") from exc
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.decode("utf-8", errors="ignore").strip() if exc.stderr else ""
        stdout = exc.stdout.decode("utf-8", errors="ignore").strip() if exc.stdout else ""
        details = stderr or stdout or str(exc)
        raise GitHelperError(details) from exc


def _ensure_git_repo() -> None:
    _run_git(["git", "rev-parse", "--is-inside-work-tree"])


def _branch_exists(name: str) -> bool:
    try:
        _run_git(["git", "rev-parse", "--verify", f"refs/heads/{name}"])
    except GitHelperError:
        return False
    return True


def _checkout_or_create_branch(name: str) -> None:
    if _branch_exists(name):
        try:
            _run_git(["git", "switch", name])
        except GitHelperError:
            _run_git(["git", "checkout", name])
        return
    try:
        _run_git(["git", "switch", "-c", name])
    except GitHelperError:
        _run_git(["git", "checkout", "-b", name])


def _apply_patch_file(patch_path: Path) -> None:
    _run_git(["git", "apply", str(patch_path)])


def _git_add(paths: Sequence[Path]) -> None:
    arg_paths = [str(p) for p in paths]
    _run_git(["git", "add", *arg_paths])


def _git_commit(message: str) -> None:
    _run_git(["git", "commit", "-m", message])


def _fingerprint_file(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha256(data).hexdigest()


def _relative_label(path: Path) -> str:
    try:
        rel = path.resolve().relative_to(Path.cwd().resolve())
        return rel.as_posix()
    except ValueError:
        return path.name


def _parse_samples_arg(value: str) -> Sequence[Tuple[float, ...]]:
    if not value:
        return []
    samples: List[Tuple[float, ...]] = []
    for raw in value.split(","):
        chunk = raw.strip()
        if not chunk:
            continue
        try:
            num = float(chunk) if "." in chunk else float(int(chunk))
        except ValueError as exc:
            raise argparse.ArgumentTypeError(
                f"valor inválido em --samples: {chunk}"
            ) from exc
        samples.append((num,))
    if not samples:
        raise argparse.ArgumentTypeError("nenhum valor válido informado em --samples")
    return samples


def _execute_suite(tests: Sequence[TestCase], label: str) -> Tuple[bool, List[str]]:
    runtime = MetaRuntime(state=MetaState())
    results = run_test_suite(runtime, list(tests))
    passed = all(r.passed for r in results)
    lines: List[str] = [
        f"[TESTCORE:{label}] total={len(results)} "
        f"passed={sum(1 for r in results if r.passed)} "
        f"failed={sum(1 for r in results if not r.passed)}"
    ]
    if not passed:
        for result in results:
            if result.passed:
                continue
            diffs = "; ".join(
                f"{d.path} expected={d.expected} actual={d.actual}"
                for d in result.field_diffs
            ) or "sem detalhes"
            lines.append(
                f"  - {result.case.name} intent={result.detected_intent or '-'} "
                f"lang={result.detected_lang or '-'} diffs={diffs}"
            )
    return passed, lines


def _run_suite(name: str) -> Tuple[bool, List[str]]:
    suite = get_suite(name)
    if suite is None:
        available = ", ".join(list_suites())
        return False, [f"Suite '{name}' desconhecida. Disponíveis: {available}"]
    return _execute_suite(suite, name)


def _run_suite_file(path: Path) -> Tuple[bool, List[str]]:
    tests = load_suite_file(path)
    return _execute_suite(tests, path.name)


def _cmd_evolve(args: argparse.Namespace) -> int:
    path = Path(args.path).expanduser()
    if not path.is_absolute():
        path = Path.cwd() / path
    if not path.exists():
        print(f"[META-EVOLVE] Arquivo não encontrado: {path}")
        return 1

    samples = _parse_samples_arg(args.samples) if args.samples else None
    request = EvolutionRequest(
        source=path.read_text(encoding="utf-8"),
        function_name=args.function,
        samples=samples or ((0,), (1,), (2,), (5,), (-3,)),
        diff_label=_relative_label(path),
    )
    result = MetaEvolution().evolve(request)
    if not result.success or not result.optimized_source:
        print(f"[META-EVOLVE] Nenhuma otimização aplicada ({result.reason}).")
        return 2

    patch_text = result.diff or ""

    suite_results = []

    if args.suite_file:
        custom_path = Path(args.suite_file)
        try:
            passed, report = _run_suite_file(custom_path)
        except SuiteFormatError as exc:
            print(f"[TESTCORE] {exc}")
            return 3
        for line in report:
            print(line)
        suite_results.append(
            {
                "type": "file",
                "source": str(custom_path),
                "status": "pass" if passed else "fail",
            }
        )
        if not passed:
            print("[META-EVOLVE] Evolução rejeitada pelos testes personalizados.")
            return 4

    suite_name = args.suite.lower() if args.suite else "none"
    if suite_name not in {"none", "skip", "off"}:
        passed, report = _run_suite(suite_name)
        for line in report:
            print(line)
        suite_results.append(
            {
                "type": "builtin",
                "source": suite_name,
                "status": "pass" if passed else "fail",
            }
        )
        if not passed:
            print("[META-EVOLVE] Evolução rejeitada pelos testes.")
            return 5
    else:
        print("[TESTCORE] testes pulados (use --suite NOME para habilitar).")

    patch_path = path.with_suffix(path.suffix + ".meta.patch")
    patch_path.write_text(patch_text, encoding="utf-8")
    analysis = result.analysis
    explanation = result.explanation
    explain_path = path.with_suffix(path.suffix + ".meta.explain.json")
    if explanation:
        explanation_payload = explanation_to_dict(explanation)
        explanation_payload["fingerprint"] = result.explanation_fingerprint
    else:
        explanation_payload = {"summary": "indisponível"}
    explain_path.write_text(
        json.dumps(explanation_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print("[META-EVOLVE] Evolução bem-sucedida.")
    print(f"  alvo: {path}:{args.function}")
    print(f"  patch: {patch_path}")
    print(f"  explicação: {explain_path}")
    print(f"  patch sha256: {result.patch_fingerprint}")
    if result.explanation_fingerprint:
        print(f"  explique sha256: {result.explanation_fingerprint}")
    if analysis:
        print(f"  custo: {analysis.cost_before} -> {analysis.cost_after}")
    if explanation:
        print(f"  resumo: {explanation.summary}")
    print("  diff preview:")
    preview = "\n".join(patch_text.splitlines()[:10]) or "(diff vazio)"
    print(preview)
    print("Revise o patch antes de aplicar manualmente.")

    git_branch = getattr(args, "git_branch", None)
    git_commit_message = getattr(args, "git_commit_message", None)
    git_requested = any(
        [
            bool(git_branch),
            bool(git_commit_message),
            bool(args.git_apply),
        ]
    )
    patch_applied = False

    if git_requested:
        try:
            _ensure_git_repo()
        except GitHelperError as exc:
            print(f"[GIT] Repositório git não detectado: {exc}")
            return 6

        if git_branch:
            try:
                _checkout_or_create_branch(git_branch)
                print(f"[GIT] Branch ativa: {git_branch}")
            except GitHelperError as exc:
                print(f"[GIT] Falha ao preparar branch '{git_branch}': {exc}")
                return 6

    if args.git_apply:
        try:
            _apply_patch_file(patch_path)
            patch_applied = True
            print("[GIT] Patch aplicado com sucesso.")
        except GitHelperError as exc:
            print(f"[GIT] Falha ao aplicar patch automaticamente: {exc}")
            return 6

    needs_auto_apply = (git_branch or git_commit_message) and not patch_applied
    if needs_auto_apply:
        try:
            _apply_patch_file(patch_path)
            patch_applied = True
            print("[GIT] Patch aplicado após preparação da branch.")
        except GitHelperError as exc:
            print(f"[GIT] Falha ao aplicar patch na branch selecionada: {exc}")
            return 6

    if git_commit_message:
        try:
            _git_add([path])
            _git_commit(git_commit_message)
            print(f"[GIT] Commit criado: {git_commit_message}")
        except GitHelperError as exc:
            print(f"[GIT] Falha ao criar commit: {exc}")
            return 6

    if args.report:
        report_payload = {
            "target": str(path),
            "function": args.function,
            "patch": str(patch_path),
            "explanation": explanation_payload,
            "analysis": {
                "cost_before": analysis.cost_before if analysis else None,
                "cost_after": analysis.cost_after if analysis else None,
            },
            "fingerprints": {
                "patch": result.patch_fingerprint,
                "explanation": result.explanation_fingerprint,
            },
            "tests": suite_results or [{"type": "builtin", "source": "skipped", "status": "skipped"}],
            "timestamp": time.time(),
        }
        Path(args.report).write_text(
            json.dumps(report_payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"[META-EVOLVE] Relatório salvo em {args.report}")

    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="metanucleus",
        description="Ferramentas auxiliares para o Metanúcleo simbólico.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    evolve = sub.add_parser(
        "evolve",
        help="Executa o pipeline de meta-evolução para uma função Python.",
    )
    evolve.add_argument("path", help="caminho do arquivo Python a otimizar")
    evolve.add_argument("function", help="nome da função dentro do arquivo")
    evolve.add_argument(
        "--suite",
        default="none",
        help="nome do suite do TESTCORE para validar o patch (padrão: none)",
    )
    evolve.add_argument(
        "--samples",
        help="lista de amostras numéricas separadas por vírgula para regressão (ex: 0,1,5)",
    )
    evolve.add_argument(
        "--suite-file",
        help="arquivo JSON com testes personalizados",
    )
    evolve.add_argument(
        "--report",
        help="salva um relatório JSON com métricas e status dos testes",
    )
    evolve.add_argument(
        "--git-apply",
        action="store_true",
        help="tenta aplicar automaticamente o patch via git apply",
    )
    evolve.add_argument(
        "--git-branch",
        help="cria/alternar para uma branch antes de aplicar o patch",
    )
    evolve.add_argument(
        "--git-commit-message",
        help="aplica o patch, faz git add e git commit com esta mensagem",
    )

    testcore_cmd = sub.add_parser(
        "testcore",
        help="Roda um suite do TESTCORE em sandbox determinístico.",
    )
    testcore_cmd.add_argument(
        "suite",
        help=f"nome do suite cadastrado (disponíveis: {', '.join(list_suites())})",
    )
    testcore_cmd.add_argument(
        "--json",
        action="store_true",
        help="imprime o resultado em JSON compacto",
    )
    testcore_cmd.add_argument(
        "--suite-file",
        help="arquivo JSON com testes personalizados",
    )

    snapshot_cmd = sub.add_parser(
        "snapshot",
        help="Exporta ou importa snapshots de estado.",
    )
    snapshot_cmd.add_argument("action", choices=["export", "import"])
    snapshot_cmd.add_argument("path")

    metrics_cmd = sub.add_parser(
        "metrics",
        help="Exibe métricas do runtime.",
    )

    audit_cmd = sub.add_parser(
        "audit",
        help="Calcula o SHA-256 de um arquivo e compara com um esperado opcional.",
    )
    audit_cmd.add_argument("path", help="arquivo a verificar")
    audit_cmd.add_argument(
        "--expect",
        help="fingerprint esperado (sha256) para comparação",
    )
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.command == "evolve":
        return _cmd_evolve(args)
    if args.command == "testcore":
        if args.suite_file:
            try:
                tests = load_suite_file(Path(args.suite_file))
            except SuiteFormatError as exc:
                print(f"[TESTCORE] {exc}")
                return 1
            runtime = MetaRuntime(state=MetaState())
            results = run_test_suite(runtime, tests)
            label = Path(args.suite_file).name
        else:
            suite = get_suite(args.suite)
            if suite is None:
                print(f"[TESTCORE] suite desconhecida: {args.suite}")
                return 1
            runtime = MetaRuntime(state=MetaState())
            results = run_test_suite(runtime, suite)
            label = args.suite

        total = len(results)
        passed = sum(1 for r in results if r.passed)
        failed = total - passed
        if args.json:
            payload = {
                "suite": label,
                "total": total,
                "passed": passed,
                "failed": failed,
                "results": [
                    {
                        "name": r.case.name,
                        "status": "OK" if r.passed else "FAIL",
                        "intent": r.detected_intent,
                        "lang": r.detected_lang,
                        "diffs": [
                            {"path": d.path, "expected": d.expected, "actual": d.actual}
                            for d in r.field_diffs
                        ],
                    }
                    for r in results
                ],
            }
            print(json.dumps(payload, ensure_ascii=False))
        else:
            print(f"[TESTCORE:{label}] total={total} passed={passed} failed={failed}")
            for result in results:
                status = "OK" if result.passed else "FAIL"
                line = (
                    f"  {status} {result.case.name}"
                    f" intent={result.detected_intent or '-'}"
                    f" lang={result.detected_lang or '-'}"
                )
                if result.field_diffs:
                    diffs = "; ".join(
                        f"{d.path} expected={d.expected} actual={d.actual}"
                        for d in result.field_diffs
                    )
                    line += f" diffs={diffs}"
                print(line)
        return 0 if failed == 0 else 2
    if args.command == "snapshot":
        runtime = MetaRuntime(state=MetaState())
        return_code = runtime.handle_request(f"/snapshot {args.action} {args.path}")
        print(return_code)
        return 0
    if args.command == "metrics":
        runtime = MetaRuntime(state=MetaState())
        print(runtime.handle_request("/metrics"))
        return 0
    if args.command == "audit":
        target = Path(args.path).expanduser()
        if not target.is_absolute():
            target = Path.cwd() / target
        if not target.exists():
            print(f"[META-AUDIT] Arquivo não encontrado: {target}")
            return 1
        digest = _fingerprint_file(target)
        print(f"[META-AUDIT] {target} sha256={digest}")
        if args.expect:
            if digest.lower() == args.expect.lower():
                print("[META-AUDIT] OK: fingerprint confere.")
                return 0
            print("[META-AUDIT] FALHA: fingerprint divergente.")
            return 2
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
