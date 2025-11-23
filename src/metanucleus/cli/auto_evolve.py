from __future__ import annotations

import argparse
import sys
from typing import Iterable, List, Optional

from metanucleus.kernel.meta_kernel import MetaKernel


def _parse_args(argv: Optional[Iterable[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="metanucleus-auto-evolve",
        description=(
            "Executa um ciclo de autoevolução simbólica do Metanúcleo "
            "com base nos logs de mismatches."
        ),
    )
    parser.add_argument(
        "domains",
        nargs="*",
        default=["all"],
        help="Domínios a evoluir: intent, rules, semantics, calculus, language ou all.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Aplica os patches diretamente no working tree.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Mostra as sugestões sem alterar arquivos.",
    )
    parser.add_argument(
        "--max-patches",
        type=int,
        default=None,
        help="Limita o número de patches retornados.",
    )
    parser.add_argument(
        "--source",
        default="cli",
        help="Identificador da origem deste ciclo (default: cli).",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Exibe os diffs completos dos patches.",
    )
    return parser.parse_args(list(argv) if argv is not None else None)


def _normalize_domains(domains: Iterable[str]) -> List[str]:
    valid = {"intent", "rules", "semantics", "calculus", "language", "all", "*"}
    normalized: List[str] = []
    for raw in domains:
        clean = raw.strip().lower()
        if clean not in valid:
            raise ValueError(f"Domínio inválido: {raw}")
        if clean in {"all", "*"}:
            return ["intent", "rules", "semantics", "calculus"]
        if clean == "language":
            clean = "semantics"
        normalized.append(clean)
    return normalized or ["intent", "calculus"]


def main(argv: Optional[Iterable[str]] = None) -> int:
    args = _parse_args(argv)
    try:
        domains = _normalize_domains(args.domains)
    except ValueError as exc:
        print(f"[metanucleus-auto-evolve] {exc}", file=sys.stderr)
        return 2

    if args.apply and args.dry_run:
        print(
            "[metanucleus-auto-evolve] --apply e --dry-run não podem ser usados juntos.",
            file=sys.stderr,
        )
        return 2

    apply_changes = args.apply and not args.dry_run

    print("[metanucleus-auto-evolve] iniciando ciclo...")
    print(f"  domínios: {', '.join(domains)}")
    print(f"  aplicar alterações: {apply_changes}")
    print(f"  max_patches: {args.max_patches}")
    print(f"  source: {args.source}")
    print()

    kernel = MetaKernel()
    try:
        patches = kernel.run_auto_evolution_cycle(
            domains=domains,
            max_patches=args.max_patches,
            apply_changes=apply_changes,
            source=args.source,
        )
    except Exception as exc:  # pragma: no cover - surfaced to CLI
        print(f"[metanucleus-auto-evolve] erro ao executar ciclo: {exc!r}", file=sys.stderr)
        return 3

    if not patches:
        print("[metanucleus-auto-evolve] nenhum patch sugerido.")
        return 0

    print(f"[metanucleus-auto-evolve] patches sugeridos: {len(patches)}")

    if args.verbose or args.dry_run:
        print("\n=== PATCHES GERADOS ===")
        for idx, patch in enumerate(patches, start=1):
            print(f"\n--- PATCH #{idx} [{patch.domain}] ---")
            print(f"Título: {patch.title}")
            if patch.description:
                print(f"Descrição: {patch.description}")
            if args.dry_run:
                print("\nDiff:\n")
                print(patch.diff)

    if apply_changes:
        print("\n[metanucleus-auto-evolve] patches aplicados ao working tree.")
    else:
        print("\n[metanucleus-auto-evolve] nada foi escrito em disco (use --apply).")

    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
