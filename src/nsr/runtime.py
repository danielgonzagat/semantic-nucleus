"""
Orquestrador do NSR: LxU → PSE → loop Φ → resposta.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import blake2b
from typing import List, Tuple

from liu import Node, operation

from .lex import tokenize, DEFAULT_LEXICON
from .operators import apply_operator
from .parser import build_struct
from .state import ISR, SessionCtx, initial_isr


@dataclass(slots=True)
class Trace:
    steps: List[str]
    digest: str = "0" * 32

    def add(self, label: str, quality: float, rels: int, ctx: int) -> None:
        entry = f"{len(self.steps)+1}:{label} q={quality:.2f} rel={rels} ctx={ctx}"
        self.steps.append(entry)
        self.digest = blake2b((self.digest + entry).encode("utf-8"), digest_size=16).hexdigest()


def run_text(text: str, session: SessionCtx | None = None) -> Tuple[str, Trace]:
    session = session or SessionCtx()
    lexicon = session.lexicon
    if not (lexicon.synonyms or lexicon.pos_hint or lexicon.qualifiers or lexicon.rel_words):
        lexicon = DEFAULT_LEXICON
    tokens = tokenize(text, lexicon)
    struct0 = build_struct(tokens)
    return run_struct(struct0, session)


def run_struct(struct_node: Node, session: SessionCtx) -> Tuple[str, Trace]:
    isr = initial_isr(struct_node, session)
    trace = Trace(steps=[])
    steps = 0
    seen_signatures = set()
    idle_loops = 0
    while steps < session.config.max_steps:
        steps += 1
        if not isr.ops_queue:
            if isr.answer.fields:
                break
            if isr.goals:
                isr.ops_queue.append(isr.goals[0])
            else:
                isr.ops_queue.extend([operation("ALIGN"), operation("STABILIZE"), operation("SUMMARIZE")])
        op = isr.ops_queue.popleft()
        isr = apply_operator(isr, op, session)
        trace.add(op.label or "NOOP", isr.quality, len(isr.relations), len(isr.context))
        signature = _state_signature(isr)
        if signature in seen_signatures:
            idle_loops += 1
            if idle_loops >= 2:
                if not isr.answer.fields:
                    fallback = isr.goals[0] if isr.goals else operation("SUMMARIZE")
                    isr.ops_queue.append(fallback)
                    idle_loops = 0
                    continue
                break
        else:
            seen_signatures.add(signature)
            idle_loops = 0
        if isr.answer.fields and isr.quality >= session.config.min_quality:
            break
    answer_field = dict(isr.answer.fields).get("answer")
    text_answer = answer_field.label if answer_field else "Não encontrei resposta."
    return text_answer or "Não encontrei resposta.", trace


def _state_signature(isr: ISR) -> str:
    answer_text = ""
    answer_field = dict(isr.answer.fields).get("answer")
    if answer_field and answer_field.label:
        answer_text = answer_field.label
    payload = f"{len(isr.relations)}|{len(isr.context)}|{answer_text}|{isr.quality:.2f}"
    return blake2b(payload.encode("utf-8"), digest_size=12).hexdigest()


__all__ = ["run_text", "run_struct", "Trace"]
