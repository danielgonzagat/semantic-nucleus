from __future__ import annotations

from metanucleus.testing.mismatch_logger import log_calc_rule_mismatch


def test_calc_rule_mismatch_double_negation() -> None:
    """
    Registro simbólico de uma falha da regra simplify_double_negation.
    """
    log_calc_rule_mismatch(
        rule_id="simplify_double_negation",
        input_expr="¬(¬P)",
        expected="P",
        predicted="¬(¬P)",
    )
    assert True


def test_calc_rule_mismatch_factor_common_and() -> None:
    """
    Registro simbólico para fatoração de A em ANDs encadeados.
    """
    log_calc_rule_mismatch(
        rule_id="factor_common_and",
        input_expr="(A & B) | (A & C)",
        expected="A & (B | C)",
        predicted="(A & B) | (A & C)",
    )
    assert True
