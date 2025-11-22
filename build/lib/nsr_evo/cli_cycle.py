from __future__ import annotations

import argparse
from pathlib import Path

from nsr_evo.energy import EnergyConfig
from nsr_evo.induction import InductionConfig
from nsr_evo.loop import energy_based_evolution_cycle


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m nsr_evo.cli_cycle",
        description="Executa um ciclo de evolução simbólica guiado por energia.",
    )
    parser.add_argument(
        "--episodes",
        default=".nsr_learning/episodes.jsonl",
        help="Caminho para o log de episódios.",
    )
    parser.add_argument(
        "--rules",
        default=".nsr_learning/learned_rules.jsonl",
        help="Caminho para o arquivo de regras aprendidas.",
    )
    parser.add_argument(
        "--max-prompts",
        type=int,
        default=32,
        help="Número máximo de prompts usados na avaliação.",
    )
    parser.add_argument(
        "--min-quality",
        type=float,
        default=0.6,
        help="Qualidade mínima considerada boa para energia e indução.",
    )
    parser.add_argument(
        "--min-support",
        type=int,
        default=3,
        help="Suporte mínimo para propor uma regra.",
    )
    parser.add_argument(
        "--max-rules",
        type=int,
        default=8,
        help="Máximo de regras candidatas aceitas por ciclo.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    ind_cfg = InductionConfig(
        min_quality=args.min_quality,
        min_support=args.min_support,
        max_new_rules_per_cycle=args.max_rules,
    )
    energy_cfg = EnergyConfig(min_quality_ok=args.min_quality)

    report = energy_based_evolution_cycle(
        episodes_path=Path(args.episodes),
        rules_path=Path(args.rules),
        max_prompts=args.max_prompts,
        induction_cfg=ind_cfg,
        energy_cfg=energy_cfg,
    )

    print(
        f"[nsr_evo] prompts={report.considered_prompts} "
        f"candidates={report.candidate_rules} accepted={report.accepted_rules}"
    )
    print(
        f"[nsr_evo] energy base={report.base_energy:.3f} "
        f"new={report.new_energy:.3f} improved={report.improved}"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
