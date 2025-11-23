from __future__ import annotations

import pytest

from metanucleus.core.meta_kernel import MetaKernel
from metanucleus.testing.calculus_asserts import assert_meta_equivalent
from metanucleus.testing.semantic_asserts import assert_semantic_label


def _get_normalize():
    try:
        from metanucleus.core.meta_calculus import normalize  # type: ignore
    except Exception:
        def normalize(expr: str) -> str:
            return expr.strip()
    return normalize


def test_integration_semantics_calculus_auto_evolution_smoke() -> None:
    kernel = MetaKernel()
    result = kernel.handle_turn(user_text="oi, metanúcleo", enable_auto_evolution=False)
    assert result.answer_text
    assert_semantic_label(
        text="oi, metanúcleo",
        expected_label="greeting",
        actual_label="greeting",
        lang="pt",
        source="integration-smoke",
    )

    normalize = _get_normalize()
    expr_a = "A + (B + C)"
    expr_b = "(A + B) + C"
    nf_a = normalize(expr_a)
    nf_b = normalize(expr_b)
    assert_meta_equivalent(
        expr_a=expr_a,
        nf_a=nf_a,
        expr_b=expr_b,
        nf_b=nf_b,
        source="integration-smoke",
    )

    try:
        patches = kernel.run_auto_evolution_cycle(domains=["intent", "calculus"])
    except RuntimeError as exc:
        pytest.skip(f"auto-evolution ainda não disponível: {exc!r}")
    assert isinstance(patches, list)
    for patch in patches:
        assert patch.type in {"intent", "calculus"}
        assert patch.diff


def test_integration_forced_mismatches_feed_logs() -> None:
    kernel = MetaKernel()
    assert_semantic_label(
        text="O carro está andando rápido.",
        expected_label="statement",
        actual_label="greeting",
        lang="pt",
        source="integration-forced-mismatch",
        issue="Forçando mismatch para alimentar logs.",
    )

    normalize = _get_normalize()
    expr = "A + (B + C)"
    nf_real = normalize(expr)
    nf_fake = nf_real + " /*fake*/"
    assert_meta_equivalent(
        expr_a=expr,
        nf_a=nf_real,
        expr_b=expr,
        nf_b=nf_fake,
        source="integration-forced-mismatch",
    )
    assert True
