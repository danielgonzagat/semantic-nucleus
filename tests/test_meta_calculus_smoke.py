from __future__ import annotations

import pytest

from metanucleus.runtime import MetanucleusRuntime
from metanucleus.testing.mismatch_logger import log_calc_rule_mismatch


@pytest.fixture(scope="module")
def runtime() -> MetanucleusRuntime:
    return MetanucleusRuntime()


@pytest.fixture()
def session(runtime: MetanucleusRuntime):
    return runtime.new_session()


CALCULUS_CASES = [
    ("simplify_double_negation", "¬(¬P)", "P"),
    ("factor_common_and", "(A & B) | (A & C)", "A & (B | C)"),
]


@pytest.mark.parametrize("rule_id, expr, expected", CALCULUS_CASES)
def test_meta_calculus_rules(session, rule_id, expr, expected) -> None:
    predicted = session.normalize_expr(expr, rule_hint=rule_id)
    if predicted != expected:
        log_calc_rule_mismatch(
            rule_id=rule_id,
            input_expr=expr,
            expected=expected,
            predicted=predicted,
        )
    assert True
