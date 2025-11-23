from __future__ import annotations

from hypothesis import assume, given, settings, strategies as st

from nsr import SessionCtx, run_text_full
from nsr.meta_transformer import meta_summary_to_dict


def _ascii_text():
    alphabet = st.characters(
        min_codepoint=32,
        max_codepoint=126,
        blacklist_categories=("Cs",),
    )
    return st.text(alphabet=alphabet, min_size=1, max_size=64)


@given(_ascii_text())
@settings(max_examples=60, deadline=None)
def test_meta_digest_is_deterministic(text_input: str) -> None:
    ctx_a = SessionCtx()
    ctx_b = SessionCtx()
    try:
        outcome_a = run_text_full(text_input, session=ctx_a)
        outcome_b = run_text_full(text_input, session=ctx_b)
    except (SyntaxError, ValueError):
        assume(False)
        return

    summary_a = meta_summary_to_dict(outcome_a.meta_summary)
    summary_b = meta_summary_to_dict(outcome_b.meta_summary)

    assert summary_a["meta_digest"] == summary_b["meta_digest"]

    exec_keys_a = sorted(k for k in summary_a if k.startswith("calc_exec_"))
    exec_keys_b = sorted(k for k in summary_b if k.startswith("calc_exec_"))
    assert exec_keys_a == exec_keys_b
    for key in exec_keys_a:
        assert summary_a[key] == summary_b[key]
