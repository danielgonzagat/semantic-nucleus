"""Simple evaluation harness for the MetaKernel."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from .metakernel import metakernel_process
from .mismatch_logger import MismatchRecord, log_mismatch


@dataclass
class EvalCase:
    text: str
    expected_intent: Optional[str] = None
    expected_semantics: Optional[str] = None
    expected_calculus: Optional[float] = None
    expected_frame_id: Optional[str] = None


EVAL_SUITE: List[EvalCase] = [
    EvalCase(text="oi", expected_intent="greeting"),
    EvalCase(text="o que é um operador?", expected_intent="question", expected_semantics="semantic_statement"),
    EvalCase(text="2 + 2", expected_calculus=4.0),
    EvalCase(text="quanto é 7 vezes 8?", expected_intent="question", expected_calculus=56.0),
    EvalCase(text="o carro bateu no muro", expected_frame_id="physical_action"),
]


def run_eval_suite() -> None:
    print("[eval] rodando suite de avaliação simbólica…")
    for case in EVAL_SUITE:
        result = metakernel_process(case.text)
        if case.expected_intent and result.intent.label != case.expected_intent:
            print(f"[eval][intent] erro: {case.text!r} esperado={case.expected_intent} obtido={result.intent.label}")
            log_mismatch(
                MismatchRecord(
                    kind="intent",
                    text=case.text,
                    expected=case.expected_intent,
                    predicted=result.intent.label,
                    extra={"reasons": result.intent.reasons, "meta_conf": result.confidence},
                )
            )
        if case.expected_semantics and result.semantics.label != case.expected_semantics:
            print(f"[eval][semantics] erro: {case.text!r} esperado={case.expected_semantics} obtido={result.semantics.label}")
            log_mismatch(
                MismatchRecord(
                    kind="semantics",
                    text=case.text,
                    expected=case.expected_semantics,
                    predicted=result.semantics.label,
                    extra={"signals": result.semantics.signals, "meta_conf": result.confidence},
                )
            )
        if case.expected_calculus is not None:
            if result.calculus.kind != "arithmetic" or result.calculus.result != case.expected_calculus:
                print(f"[eval][calc] erro: {case.text!r} esperado={case.expected_calculus} obtido={result.calculus.result}")
                log_mismatch(
                    MismatchRecord(
                        kind="calculus",
                        text=case.text,
                        expected=str(case.expected_calculus),
                        predicted=str(result.calculus.result),
                        extra={
                            "expr": result.calculus.expression_normalized,
                            "steps": result.calculus.steps,
                        },
                    )
                )
        if case.expected_frame_id is not None:
            predicted_frame = result.frames.frame_id or ""
            if predicted_frame != case.expected_frame_id:
                print(
                    f"[eval][frame] erro: {case.text!r} esperado={case.expected_frame_id} "
                    f"obtido={predicted_frame or result.frames.frame_type}"
                )
                log_mismatch(
                    MismatchRecord(
                        kind="semantics",
                        text=case.text,
                        expected=case.expected_frame_id,
                        predicted=predicted_frame or result.frames.frame_type,
                        extra={
                            "type": "frame",
                            "frame_type": result.frames.frame_type,
                            "roles": result.frames.roles,
                        },
                    )
                )
    print("[eval] suite completa.")


if __name__ == "__main__":
    run_eval_suite()
