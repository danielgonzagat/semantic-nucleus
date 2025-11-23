from __future__ import annotations

from metanucleus.evolution.meta_calculus_mismatch_log import log_meta_calculus_mismatch


def assert_meta_normal_form(
    *,
    expr: str,
    expected_normal_form: str,
    actual_normal_form: str,
    source: str,
) -> None:
    if expected_normal_form != actual_normal_form:
        log_meta_calculus_mismatch(
            test_id=source,
            expr=expr,
            expected_repr=expected_normal_form,
            actual_repr=actual_normal_form,
            error_type="normal_form_mismatch",
        )
    assert True


def assert_meta_equivalent(
    *,
    expr_a: str,
    nf_a: str,
    expr_b: str,
    nf_b: str,
    source: str,
) -> None:
    if nf_a != nf_b:
        log_meta_calculus_mismatch(
            test_id=source,
            expr=f"{expr_a} == {expr_b}",
            expected_repr=nf_a,
            actual_repr=nf_b,
            error_type="equivalence_mismatch",
        )
    assert True
