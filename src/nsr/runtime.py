"""
Orquestrador do NSR: LxU → PSE → loop Φ → resposta.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import List, Tuple

from liu import Node, operation, struct

from .lex import tokenize, DEFAULT_LEXICON
from .operators import apply_operator
from .parser import build_struct
from .state import ISR, SessionCtx, initial_isr


@dataclass(slots=True)
class Trace:
    steps: List[str]

    def add(self, message: str) -> None:
        self.steps.append(message)


def run_text(text: str, session: SessionCtx | None = None) -> Tuple[str, Trace]:
    session = session or SessionCtx()
    tokens = tokenize(text, session.lexicon or DEFAULT_LEXICON)
    struct0 = build_struct(tokens)
    return run_struct(struct0, session)


def run_struct(struct_node: Node, session: SessionCtx) -> Tuple[str, Trace]:
    isr = initial_isr(struct_node, session)
    trace = Trace(steps=[])
    steps = 0
    while steps < session.config.max_steps:
        steps += 1
        if not isr.ops_queue:
            if isr.answer.fields:
                break
            if isr.goals:
                isr.ops_queue.append(isr.goals[0])
            else:
                isr.ops_queue.append(operation("SUMMARIZE"))
        op = isr.ops_queue.popleft()
        before_quality = isr.quality
        isr = apply_operator(isr, op, session)
        trace.add(f"{steps}: {op.label} quality={isr.quality:.2f}")
        if isr.answer.fields and isr.quality >= session.config.min_quality:
            break
    answer_field = dict(isr.answer.fields).get("answer")
    text_answer = answer_field.label if answer_field else "Não encontrei resposta."
    return text_answer or "Não encontrei resposta.", trace


__all__ = ["run_text", "run_struct", "Trace"]
