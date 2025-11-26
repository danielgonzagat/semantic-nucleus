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
    parser.add_argument(
        "--include-lc-meta",
        action="store_true",
        help="Inclui o pacote `lc_meta` serializado quando o MetaTransformer produzir cálculo LC-Ω.",
    )
    parser.add_argument(
        "--include-code-summary",
        action="store_true",
        help="Inclui o resumo de código (`code_ast_summary`) serializado quando disponível.",
    )
    parser.add_argument(
        "--include-equation-trend",
        action="store_true",
        help="Inclui resumo determinístico da meta-equação (digests, trend e deltas estruturais).",
    )
    parser.add_argument(
        "--include-proof",
        action="store_true",
        help="Inclui o bloco meta_proof (Φ_PROVE) com verdade/query/digest determinísticos quando disponível.",
    )
    parser.add_argument(
        "--calc-mode",
        choices=("hybrid", "plan_only", "skip"),
        default=None,
        help="Define como o runtime executa planos ΣVM: híbrido (padrão), apenas plano ou ignorar planos.",
    )
    parser.add_argument(
        "--expect-meta-digest",
        help="Verifica se o meta_digest calculado coincide com o valor informado; falha se divergir.",
    )
    parser.add_argument(
        "--expect-code-digest",
        help="Verifica se o code_summary_digest coincide com o valor informado (requer --include-meta e código detectado).",
    )
    parser.add_argument(
        "--expect-code-functions",
        type=int,
        help="Verifica se o resumo de código detectou exatamente N funções.",
    )
    parser.add_argument(
        "--expect-code-function-name",
        action="append",
        help="Garante que o resumo de código contém uma função com o nome informado (pode repetir a flag).",
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
    session.config.memory_store_path = None
    session.config.episodes_path = None
    session.config.induction_rules_path = None
    session.meta_buffer = tuple()
    if args.disable_contradictions:
        session.config.enable_contradiction_check = False
    elif args.enable_contradictions:
        session.config.enable_contradiction_check = True
    if args.max_steps is not None:
        session.config.max_steps = args.max_steps
    if args.min_quality is not None:
        session.config.min_quality = args.min_quality
    if args.calc_mode is not None:
        session.config.calc_mode = args.calc_mode

    outcome = run_text_full(args.text, session)
    if args.expect_meta_digest:
        if not outcome.meta_summary:
            raise SystemExit("expect-meta-digest requer meta_summary (use --include-meta).")
        summary_dict = meta_summary_to_dict(outcome.meta_summary)
        digest = summary_dict.get("meta_digest", "")
        if not digest:
            raise SystemExit("meta_digest indisponível para comparação.")
        if digest.lower() != args.expect_meta_digest.lower():
            raise SystemExit(f"meta_digest divergente: esperado {args.expect_meta_digest}, obtido {digest}.")
    summary_data = _extract_code_summary_data(outcome)
    if args.expect_code_digest:
        if summary_data is None or not summary_data.get("digest"):
            raise SystemExit("code_summary_digest indisponível para comparação.")
        if summary_data["digest"].lower() != args.expect_code_digest.lower():
            raise SystemExit(
                f"code_summary_digest divergente: esperado {args.expect_code_digest}, obtido {summary_data['digest']}."
            )
    if args.expect_code_functions is not None:
        if summary_data is None:
            raise SystemExit("expect-code-functions requer um resumo de código (rota CODE ou --include-code-summary).")
        fn_count = summary_data.get("function_count")
        if fn_count is None:
            raise SystemExit("Resumo de código não contém contagem de funções.")
        if fn_count != args.expect_code_functions:
            raise SystemExit(
                f"code_summary_function_count divergente: esperado {args.expect_code_functions}, obtido {fn_count}."
            )
    if args.expect_code_function_name:
        if summary_data is None or not summary_data.get("functions"):
            raise SystemExit("expect-code-function-name requer um resumo de código (rota CODE ou --include-code-summary).")
        functions = summary_data.get("functions") or []
        missing = [name for name in args.expect_code_function_name if name not in functions]
        if missing:
            raise SystemExit(
                f"Funções ausentes no resumo: {', '.join(sorted(set(missing)))}."
            )
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
    if args.include_lc_meta and outcome.lc_meta is not None:
        payload["lc_meta"] = to_json(outcome.lc_meta)
    if args.include_code_summary and outcome.code_summary is not None:
        payload["code_summary"] = to_json(outcome.code_summary)
    if args.include_equation_trend:
        equation_meta = _extract_equation_trend_data(outcome)
        if equation_meta is None:
            raise SystemExit("--include-equation-trend requer meta_summary (use --include-meta).")
        payload["equation_trend_detail"] = equation_meta
    if args.include_proof:
        proof_meta = _extract_logic_proof_data(outcome)
        if proof_meta is None:
            raise SystemExit("--include-proof requer meta_summary e uma consulta lógica (use --include-meta).")
        payload["proof_detail"] = proof_meta

    serialized = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    if args.output:
        Path(args.output).write_text(serialized + "\n", encoding="utf-8")
    print(serialized)
    return 0


def _extract_code_summary_data(outcome) -> dict[str, object] | None:
    digest = None
    fn_count = None
    node_count = None
    language = None
    function_names: list[str] | None = None
    function_details: list[dict[str, object]] | None = None
    if outcome.meta_summary:
        summary_dict = meta_summary_to_dict(outcome.meta_summary)
        digest = summary_dict.get("code_summary_digest") or None
        fn = summary_dict.get("code_summary_function_count")
        nc = summary_dict.get("code_summary_node_count")
        lang = summary_dict.get("code_summary_language")
        fn_details = summary_dict.get("code_summary_function_details")
        if isinstance(fn_details, list):
            function_details = fn_details
            function_names = [str(item.get("name")) for item in fn_details if item.get("name")]
        fn_names = summary_dict.get("code_summary_functions")
        if fn is not None:
            fn_count = int(fn)
        if nc is not None:
            node_count = int(nc)
        if lang:
            language = lang
        if function_names is None and isinstance(fn_names, list):
            function_names = [str(item) for item in fn_names if isinstance(item, str)]
        if digest and fn_count is not None:
            return {
                "digest": digest,
                "function_count": fn_count,
                "node_count": node_count,
                "language": language,
                "functions": function_names,
                "function_details": function_details,
            }
    if outcome.code_summary is not None:
        summary_json = json.loads(to_json(outcome.code_summary))
        fields = summary_json.get("fields") or {}
        digest = fields.get("digest", {}).get("label")
        fn_node = fields.get("function_count")
        node_node = fields.get("node_count")
        lang_node = fields.get("language")
        functions_node = fields.get("functions")
        if fn_node is not None:
            fn_count = int(fn_node.get("value", 0))
        if node_node is not None:
            node_count = int(node_node.get("value", 0))
        if lang_node is not None:
            language = lang_node.get("label")
        function_details = None
        if functions_node and functions_node.get("kind") == "LIST":
            items = functions_node.get("args") or []
            names: list[str] = []
            details: list[dict[str, object]] = []
            for item in items:
                entry_fields = item.get("fields") or {}
                name_field = entry_fields.get("name")
                name_value = name_field.get("label") if name_field else ""
                if name_value:
                    names.append(name_value)
                detail: dict[str, object] = {"name": name_value}
                param_count_field = entry_fields.get("param_count")
                if param_count_field and param_count_field.get("value") is not None:
                    detail["param_count"] = int(param_count_field["value"])
                params_field = entry_fields.get("parameters")
                if params_field and params_field.get("kind") == "LIST":
                    detail["parameters"] = [arg.get("label", "") for arg in params_field.get("args", [])]
                details.append(detail)
            function_names = names
            function_details = details
        result = {
            "digest": digest,
            "function_count": fn_count,
            "node_count": node_count,
            "language": language,
            "functions": function_names,
            "function_details": function_details,
        }
        if digest:
            return result
    calc_result = getattr(outcome, "calc_result", None)
    if calc_result and calc_result.snapshot:
        snapshot = calc_result.snapshot
        summary_json = snapshot.get("code_summary")
        if summary_json:
            fields = summary_json.get("fields") or {}
            digest = fields.get("digest", {}).get("label")
            fn_node = fields.get("function_count")
            node_node = fields.get("node_count")
            lang_node = fields.get("language")
            fn_count = int(fn_node.get("value", 0)) if fn_node and fn_node.get("value") is not None else None
            node_count = int(node_node.get("value", 0)) if node_node and node_node.get("value") is not None else None
            language = lang_node.get("label") if lang_node else None
            function_names = snapshot.get("code_summary_functions")
            function_details = snapshot.get("code_summary_function_details")
            return {
                "digest": digest,
                "function_count": fn_count,
                "node_count": node_count,
                "language": language,
                "functions": function_names,
                "function_details": function_details,
            }
    return None


def _extract_equation_trend_data(outcome) -> dict[str, object] | None:
    if not outcome.meta_summary:
        return None
    summary_dict = meta_summary_to_dict(outcome.meta_summary)
    digest = summary_dict.get("equation_digest")
    if not digest:
        return None
    eq_data: dict[str, object] = {
        "digest": digest,
        "input_digest": summary_dict.get("equation_input_digest"),
        "answer_digest": summary_dict.get("equation_answer_digest"),
        "quality": summary_dict.get("equation_quality"),
        "trend": summary_dict.get("equation_trend"),
    }
    delta_quality = summary_dict.get("equation_delta_quality")
    if delta_quality is not None:
        eq_data["delta_quality"] = delta_quality
    sections = summary_dict.get("equation_sections")
    if sections:
        eq_data["sections"] = sections
    delta_sections = summary_dict.get("equation_section_deltas")
    if delta_sections:
        eq_data["section_deltas"] = delta_sections
    return eq_data


def _extract_logic_proof_data(outcome) -> dict[str, object] | None:
    if not outcome.meta_summary:
        return None
    summary_dict = meta_summary_to_dict(outcome.meta_summary)
    proof_payload = summary_dict.get("logic_proof")
    truth = summary_dict.get("logic_proof_truth")
    query = summary_dict.get("logic_proof_query")
    digest = summary_dict.get("logic_proof_digest")
    if not (proof_payload or truth or query or digest):
        return None
    proof_data: dict[str, object] = {
        "truth": truth or "unknown",
        "query": query or "",
        "digest": digest or "",
    }
    if proof_payload:
        proof_data["proof"] = proof_payload
    return proof_data


if __name__ == "__main__":
    sys.exit(main())
