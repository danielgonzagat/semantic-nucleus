"""
Interface de linha de comando para o NSR → Equação → Texto.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict

from . import SessionCtx, run_text_full


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
    parser.add_argument(
        "--enable-contradictions",
        action="store_true",
        help="Ativa a checagem determinística de contradições.",
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
    if args.enable_contradictions:
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

    serialized = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    if args.output:
        Path(args.output).write_text(serialized + "\n", encoding="utf-8")
    print(serialized)
    return 0


if __name__ == "__main__":
    sys.exit(main())
