from __future__ import annotations

import argparse
import sys
from typing import Iterable, List, Optional

from datetime import datetime, timezone
from pathlib import Path

from metanucleus.kernel.meta_kernel import MetaKernel, AutoEvolutionFilters
from metanucleus.evolution.report import write_auto_evolve_report
from metanucleus.utils.project import get_project_root

PROJECT_ROOT = get_project_root(Path(__file__))
REPORT_PATH = PROJECT_ROOT / ".metanucleus" / "auto_evolve_last.json"


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
        help=(
            "Domínios a evoluir: intent, rules, semantics, semantic_frames, "
            "meta_calculus (alias calculus), language ou all."
        ),
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
        "--log-since",
        help="Considera apenas mismatches registrados a partir deste timestamp ISO (ex.: 2025-01-01T00:00:00Z).",
    )
    parser.add_argument(
        "--frame-language",
        action="append",
        default=None,
        help="Filtra frame_mismatch por idioma (pode repetir).",
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


def _parse_iso8601(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    cleaned = value.strip()
    if not cleaned:
        return None
    if cleaned.endswith("Z"):
        cleaned = cleaned[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(cleaned).astimezone(timezone.utc)
    except ValueError:
        raise SystemExit(f"[metanucleus-auto-evolve] Timestamp inválido: {value!r}")


def _normalize_domains(domains: Iterable[str]) -> List[str]:
    valid = {
        "intent",
        "rules",
        "semantics",
        "semantic_frames",
        "meta_calculus",
        "calculus",
        "language",
        "all",
        "*",
    }
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
    log_since = _parse_iso8601(args.log_since)
    frame_languages = {code.lower() for code in (args.frame_language or []) if code}
    filters = AutoEvolutionFilters(
        log_since=log_since,
        frame_languages=frame_languages or None,
    )

    report_meta = {
        "cli": "metanucleus-auto-evolve",
        "commit_requested": args.commit,
        "dry_run": args.dry_run,
        "frame_languages": sorted(frame_languages),
    }

    try:
        patches = kernel.run_auto_evolution_cycle(
            domains=domains,
            max_patches=args.max_patches,
            apply_changes=apply_changes,
            source=args.source,
            filters=filters,
            report_path=REPORT_PATH,
            report_metadata=report_meta,
        )
    except Exception as exc:  # pragma: no cover - surfaced to CLI
        print(f"[metanucleus-auto-evolve] erro ao executar ciclo: {exc!r}", file=sys.stderr)
        return 3

    eval_stats = getattr(kernel, "last_evolution_stats", [])
    if eval_stats:
        print("[metanucleus-auto-evolve] domínios analisados:")
        for entry in eval_stats:
            reason = entry.get("reason")
            duration = entry.get("duration_ms")
            details = []
            if reason:
                details.append(reason)
            if duration is not None:
                details.append(f"{duration} ms")
            entries = entry.get("entries_scanned")
            if entries is not None:
                details.append(f"{entries} entradas")
            suffix = f" ({'; '.join(details)})" if details else ""
            print(f"  - {entry.get('domain')}: {entry.get('status')}{suffix}")
        print()

    write_auto_evolve_report(
        REPORT_PATH,
        domains=domains,
        patches=patches,
        domain_stats=eval_stats,
        filters=filters,
        applied=apply_changes,
        source=args.source,
        max_patches=args.max_patches,
        extra=report_meta,
    )

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
