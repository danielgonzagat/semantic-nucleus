from __future__ import annotations

from metanucleus.core.meta_kernel import MetaKernel
from metanucleus.testing.calculus_asserts import (
    assert_meta_equivalent,
    assert_meta_normal_form,
)
from metanucleus.testing.semantic_asserts import assert_semantic_label


def _run_pipeline_and_get_struct(kernel: MetaKernel, phrase: str):
    answer_text, answer_struct, debug_info, meta_summary, calc_exec = kernel._run_symbolic_pipeline(  # type: ignore[attr-defined]
        user_text=phrase
    )
    if meta_summary and "meta_summary" not in debug_info:
        debug_info["meta_summary"] = meta_summary
    if calc_exec and "calc_exec" not in debug_info:
        debug_info["calc_exec"] = calc_exec
    return answer_struct, debug_info


def test_meta_kernel_pipeline_exposes_meta_summary() -> None:
    kernel = MetaKernel()
    answer_struct, debug_info = _run_pipeline_and_get_struct(kernel, "Um carro existe.")
    assert answer_struct is not None
    assert "meta_summary" in debug_info
    assert debug_info["meta_summary"]["route"] == "text"
    assert debug_info["trace_digest"]
    assert kernel.state.meta_history, "Meta history should mirror NSR summaries."


def _check_semantic_frame(
    kernel: MetaKernel, phrase: str, lang: str, expected_repr: str, issue: str
) -> None:
    answer_struct, debug_info = _run_pipeline_and_get_struct(kernel, phrase)
    actual_repr = repr(answer_struct)
    assert_semantic_label(
        text=phrase,
        expected_label=expected_repr,
        actual_label=actual_repr,
        lang=lang,
        source="runtime-semantic-integration",
        issue=issue,
        expected_repr=expected_repr,
        actual_repr=actual_repr,
        extra={"debug_info": debug_info},
    )


def test_runtime_semantics_pt_sentence() -> None:
    kernel = MetaKernel()
    expected = "STRUCT(subject=ENTITY('carro'), action=ENTITY('andar'), modifier=[ENTITY('rápido')])"
    _check_semantic_frame(
        kernel=kernel,
        phrase="O carro está andando rápido.",
        lang="pt",
        expected_repr=expected,
        issue="Frame PT-BR carro/andar/rápido não corresponde ao esperado.",
    )


def test_runtime_semantics_en_sentence() -> None:
    kernel = MetaKernel()
    expected = "STRUCT(subject=ENTITY('car'), action=ENTITY('move'), modifier=[ENTITY('fast')])"
    _check_semantic_frame(
        kernel=kernel,
        phrase="The car is moving fast.",
        lang="en",
        expected_repr=expected,
        issue="Frame EN car/move/fast não corresponde ao esperado.",
    )


def test_runtime_meta_calculus_logging() -> None:
    expr = "A + (B + C)"
    nf_real = expr.strip()
    nf_fake = nf_real + " /*fake*/"
    assert_meta_normal_form(
        expr=expr,
        expected_normal_form=nf_fake,
        actual_normal_form=nf_real,
        source="runtime-semantic-integration",
    )
    assert_meta_equivalent(
        expr_a="A + (B + C)",
        nf_a=nf_real,
        expr_b="(A + B) + C",
        nf_b=nf_fake,
        source="runtime-semantic-integration",
    )
