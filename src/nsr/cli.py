"""
Interface de linha de comando para o NSR → Equação → Texto.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict

from liu import to_json

from . import SessionCtx, run_text_full
from .meta_transformer import meta_summary_to_dict


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m nsr.cli",
        description="Executa o NSR e exporta a equação LIU correspondente.",
    )
    parser.add_argument("text", help="Entrada textual (qualquer idioma).")
    parser.add_argument(
        "--format",
        choices=("json", "sexpr", "both"),
        default="both",
        help="Formato do bundle de equação a ser emitido.",
    )
    parser.add_argument(
        "--output",
        help="Arquivo de saída (JSON). Quando omitido, imprime no stdout.",
    )
    contradiction_group = parser.add_mutually_exclusive_group()
    contradiction_group.add_argument(
        "--enable-contradictions",
        action="store_true",
        help="Mantém compatibilidade e força a checagem determinística de contradições (já habilitada por padrão).",
    )
    contradiction_group.add_argument(
        "--disable-contradictions",
        action="store_true",
        help="Desativa explicitamente a checagem determinística de contradições.",
    )
    parser.add_argument("--max-steps", type=int, help="Sobrescreve Config.max_steps.")
    parser.add_argument("--min-quality", type=float, help="Sobrescreve Config.min_quality.")
    parser.add_argument(
        "--include-report",
        action="store_true",
        help="Inclui relatório determinístico texto←equação no payload final.",
    )
    parser.add_argument(
        "--include-stats",
        action="store_true",
        help="Inclui contagens/digests determinísticos (auditoria estrutural).",
    )
    parser.add_argument(
        "--include-explanation",
        action="store_true",
        help="Inclui narrativa determinística Equação→Texto baseada no estado final.",
    )
    parser.add_argument(
        "--include-meta",
        action="store_true",
        help="Inclui meta_summary (meta_route/meta_input/meta_output) no payload final.",
    )
    parser.add_argument(
        "--include-calc",
        action="store_true",
        help="Inclui descrição e snapshot do MetaCalculationPlan executado (se existir).",
    )
    return parser


def _build_equation_bundle(outcome, fmt: str) -> Dict[str, Any]:
    bundle: Dict[str, Any] = {}
    if fmt in ("json", "both"):
        bundle["json"] = outcome.equation.to_json_bundle()
    if fmt in ("sexpr", "both"):
        bundle["sexpr"] = outcome.equation.to_sexpr_bundle()
    return bundle


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    session = SessionCtx()
    if args.disable_contradictions:
        session.config.enable_contradiction_check = False
    elif args.enable_contradictions:
        session.config.enable_contradiction_check = True
    if args.max_steps is not None:
        session.config.max_steps = args.max_steps
    if args.min_quality is not None:
        session.config.min_quality = args.min_quality

    outcome = run_text_full(args.text, session)
    payload = {
        "answer": outcome.answer,
        "quality": outcome.quality,
        "halt_reason": outcome.halt_reason.value,
        "trace_digest": outcome.trace.digest,
        "equation_hash": outcome.equation_digest,
        "steps": outcome.trace.steps,
        "invariant_failures": outcome.trace.invariant_failures,
        "contradictions": [
            {
                "label": contradiction.base_label,
                "positive": contradiction.positive.label,
                "negative": contradiction.negative.label,
            }
            for contradiction in outcome.trace.contradictions
        ],
        "equation": _build_equation_bundle(outcome, args.format),
    }
    if args.include_report:
        payload["equation_report"] = outcome.equation.to_text_report()
    if args.include_stats:
        payload["equation_stats"] = outcome.equation.stats().to_dict()
    if args.include_explanation:
        payload["explanation"] = outcome.explanation
    if args.include_meta and outcome.meta_summary:
        payload["meta_summary"] = meta_summary_to_dict(outcome.meta_summary)
    if args.include_calc and outcome.calc_result:
        calc_payload: Dict[str, Any] = {
            "plan": outcome.calc_result.plan.description,
            "error": outcome.calc_result.error,
            "consistent": outcome.calc_result.consistent,
        }
        if outcome.calc_result.answer is not None:
            calc_payload["answer"] = to_json(outcome.calc_result.answer)
        if outcome.calc_result.snapshot is not None:
            calc_payload["snapshot"] = outcome.calc_result.snapshot
        payload["meta_calc"] = calc_payload

    serialized = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    if args.output:
        Path(args.output).write_text(serialized + "\n", encoding="utf-8")
    print(serialized)
    return 0


if __name__ == "__main__":
    sys.exit(main())
