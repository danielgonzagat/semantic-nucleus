from metanucleus import MetaRuntime, MetaState
from metanucleus.test.testcore import (
    Expected,
    TestCase,
    run_testcase,
)


def test_testcore_passes_on_greeting():
    runtime = MetaRuntime(state=MetaState())
    tc = TestCase(
        name="saudacao",
        input_text="Oi Metanúcleo!",
        expected=Expected(intent="greeting", lang="pt", answer_contains="Metanúcleo"),
    )
    result = run_testcase(runtime, tc)
    assert result.passed
    assert result.field_diffs == []


def test_testcore_reports_lang_diff():
    runtime = MetaRuntime(state=MetaState())
    tc = TestCase(
        name="english_question",
        input_text="Explain 2 + 2 please",
        expected=Expected(lang="en"),
    )
    result = run_testcase(runtime, tc)
    assert not result.passed
    assert any(diff.path == "utterance.lang" for diff in result.field_diffs)
    assert result.patch is not None
    assert result.patch.module in {"LANGUAGE", "CORE"}
