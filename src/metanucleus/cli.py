"""
Interface de linha de comando para o pipeline de meta-evolução.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Iterable, List, Sequence, Tuple

from metanucleus.core.evolution import EvolutionRequest, MetaEvolution
from metanucleus.core.state import MetaState
from metanucleus.runtime.meta_runtime import MetaRuntime
from metanucleus.runtime.test_suites import get_suite, list_suites
from metanucleus.test.testcore import run_test_suite


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


def _run_suite(name: str) -> Tuple[bool, List[str]]:
    suite = get_suite(name)
    if suite is None:
        available = ", ".join(list_suites())
        return False, [f"Suite '{name}' desconhecida. Disponíveis: {available}"]

    runtime = MetaRuntime(state=MetaState())
    results = run_test_suite(runtime, suite)
    passed = all(r.passed for r in results)
    lines: List[str] = [
        f"[TESTCORE] suite={name} status={'PASS' if passed else 'FAIL'} "
        f"({sum(1 for r in results if r.passed)}/{len(results)})"
    ]
    if not passed:
        for result in results:
            if result.passed:
                continue
            diffs = "; ".join(
                f"{d.path} expected={d.expected} actual={d.actual}"
                for d in result.field_diffs
            ) or "sem detalhes"
            lines.append(f"  - {result.case.name}: {diffs}")
    return passed, lines


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
    )
    result = MetaEvolution().evolve(request)
    if not result.success or not result.optimized_source:
        print(f"[META-EVOLVE] Nenhuma otimização aplicada ({result.reason}).")
        return 2

    patch_text = result.diff or ""

    if args.suite and args.suite.lower() not in {"none", "skip", "off"}:
        passed, report = _run_suite(args.suite.lower())
        for line in report:
            print(line)
        if not passed:
            print("[META-EVOLVE] Evolução rejeitada pelos testes.")
            return 3
    else:
        print("[TESTCORE] testes pulados (use --suite NOME para habilitar).")

    patch_path = path.with_suffix(path.suffix + ".meta.patch")
    patch_path.write_text(patch_text, encoding="utf-8")
    analysis = result.analysis

    print("[META-EVOLVE] Evolução bem-sucedida.")
    print(f"  alvo: {path}:{args.function}")
    print(f"  patch: {patch_path}")
    if analysis:
        print(f"  custo: {analysis.cost_before} -> {analysis.cost_after}")
    print("  diff preview:")
    preview = "\n".join(patch_text.splitlines()[:10]) or "(diff vazio)"
    print(preview)
    print("Revise o patch antes de aplicar manualmente.")

    # opcional: persistir versão otimizada? por segurança, apenas sugerimos patch
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
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.command == "evolve":
        return _cmd_evolve(args)
    if args.command == "testcore":
        suite = get_suite(args.suite)
        if suite is None:
            print(f"[TESTCORE] suite desconhecida: {args.suite}")
            return 1
        runtime = MetaRuntime(state=MetaState())
        results = run_test_suite(runtime, suite)
        total = len(results)
        passed = sum(1 for r in results if r.passed)
        failed = total - passed
        if args.json:
            import json

            payload = {
                "suite": args.suite,
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
            print(
                f"[TESTCORE:{args.suite}] total={total} passed={passed} failed={failed}"
            )
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

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
