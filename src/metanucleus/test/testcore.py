"""
TESTCORE v1.0 — harness determinístico para evolução supervisionada.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, List, Optional, TYPE_CHECKING

from metanucleus.core.liu import Node, NodeKind

if TYPE_CHECKING:
    from metanucleus.runtime.meta_runtime import MetaRuntime


@dataclass(slots=True)
class Expected:
    intent: Optional[str] = None
    lang: Optional[str] = None
    answer_prefix: Optional[str] = None
    answer_contains: Optional[str] = None


@dataclass(slots=True)
class TestCase:
    name: str
    input_text: str
    expected: Expected
    __test__ = False


@dataclass(slots=True)
class FieldDiff:
    path: str
    expected: Any
    actual: Any


@dataclass(slots=True)
class PatchSuggestion:
    module: str
    reason: str
    hints: dict[str, Any]


@dataclass(slots=True)
class TestResult:
    case: TestCase
    passed: bool
    field_diffs: List[FieldDiff]
    raw_answer: str
    detected_intent: str
    detected_lang: str
    patch: Optional[PatchSuggestion]


def run_testcase(runtime: "MetaRuntime", testcase: TestCase) -> TestResult:
    answer = runtime.handle_request(testcase.input_text)
    isr = runtime.state.isr
    utter = _last_utterance(isr.context)
    detected_lang = _node_field_text(utter, "lang")
    detected_intent = _node_field_text(utter, "intent")
    answer_text = _answer_text(isr) or answer

    diffs: List[FieldDiff] = []

    exp = testcase.expected
    if exp.intent and exp.intent != detected_intent:
        diffs.append(FieldDiff("utterance.intent", exp.intent, detected_intent))
    if exp.lang and exp.lang != detected_lang:
        diffs.append(FieldDiff("utterance.lang", exp.lang, detected_lang))
    if exp.answer_prefix and not answer_text.startswith(exp.answer_prefix):
        diffs.append(
            FieldDiff(
                "answer.prefix",
                exp.answer_prefix,
                answer_text[: len(exp.answer_prefix)],
            )
        )
    if exp.answer_contains and exp.answer_contains not in answer_text:
        diffs.append(FieldDiff("answer.contains", exp.answer_contains, answer_text))

    patch = _generate_patch(testcase, diffs)
    return TestResult(
        case=testcase,
        passed=not diffs,
        field_diffs=diffs,
        raw_answer=answer_text,
        detected_intent=detected_intent,
        detected_lang=detected_lang,
        patch=patch,
    )


def run_test_suite(runtime: "MetaRuntime", tests: List[TestCase]) -> List[TestResult]:
    return [run_testcase(runtime, tc) for tc in tests]


def print_report(results: List[TestResult]) -> None:
    total = len(results)
    passed = sum(1 for r in results if r.passed)
    failed = total - passed
    print(f"\n=== TESTCORE REPORT ===")
    print(f"Total: {total} | Passaram: {passed} | Falharam: {failed}\n")
    for result in results:
        status = "OK " if result.passed else "FAIL"
        print(f"[{status}] {result.case.name}")
        print(f"  input: {result.case.input_text!r}")
        print(f"  intent={result.detected_intent!r} lang={result.detected_lang!r}")
        print(f"  answer: {result.raw_answer!r}")
        if result.field_diffs:
            print("  diffs:")
            for diff in result.field_diffs:
                print(f"    - {diff.path}: expected={diff.expected!r}, actual={diff.actual!r}")
        if result.patch:
            print("  patch suggestion:")
            print(f"    module: {result.patch.module}")
            print(f"    reason: {result.patch.reason}")
            if result.patch.hints:
                print("    hints:")
                for key, value in result.patch.hints.items():
                    print(f"      {key}: {value!r}")
        print()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _last_utterance(context: List[Node]) -> Optional[Node]:
    for node in reversed(context):
        if node.kind is NodeKind.STRUCT and _node_field_text(node, "kind") == "utterance":
            return node
    return None


def _node_field_text(node: Optional[Node], field: str) -> str:
    if not node or node.kind is not NodeKind.STRUCT:
        return ""
    child = node.fields.get(field)
    if child and child.kind is NodeKind.TEXT and child.label:
        return child.label
    return ""


def _answer_text(isr) -> str:
    answer = isr.answer
    if answer.kind is NodeKind.STRUCT and "answer" in answer.fields:
        inner = answer.fields["answer"]
        if inner.kind is NodeKind.TEXT and inner.label:
            return inner.label
    if answer.kind is NodeKind.TEXT and answer.label:
        return answer.label
    return ""


def _node_text(node: Optional[Node]) -> str:
    if not node:
        return ""
    if node.kind is NodeKind.TEXT and node.label:
        return node.label
    if node.kind is NodeKind.NUMBER and node.value_num is not None:
        return str(node.value_num)
    return ""


def _generate_patch(testcase: TestCase, diffs: List[FieldDiff]) -> Optional[PatchSuggestion]:
    if not diffs:
        return None
    for diff in diffs:
        if diff.path == "utterance.intent":
            return PatchSuggestion(
                module="INTENT",
                reason=f"Esperado intent {diff.expected!r} mas obtido {diff.actual!r}",
                hints={
                    "input": testcase.input_text,
                    "expected": diff.expected,
                    "actual": diff.actual,
                },
            )
    for diff in diffs:
        if diff.path == "utterance.lang":
            return PatchSuggestion(
                module="LANGUAGE",
                reason="Língua detectada divergiu do esperado",
                hints={"diff": asdict(diff)},
            )
    for diff in diffs:
        if diff.path.startswith("answer."):
            return PatchSuggestion(
                module="ANSWER",
                reason="Resposta textual não corresponde ao esperado",
                hints={"diff": asdict(diff)},
            )
    return PatchSuggestion(
        module="CORE",
        reason="Diferenças estruturais detectadas",
        hints={"diffs": [asdict(d) for d in diffs]},
    )
