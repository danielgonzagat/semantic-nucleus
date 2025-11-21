"""
Orquestrador do NSR: LxU → PSE → loop Φ → resposta.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from hashlib import blake2b
from typing import Iterable, List, Tuple

from liu import Node, operation, fingerprint

from .consistency import Contradiction, detect_contradictions
from .equation import EquationSnapshot, snapshot_equation
from .lex import tokenize, DEFAULT_LEXICON
from .operators import apply_operator
from .parser import build_struct
from .state import ISR, SessionCtx, initial_isr


@dataclass(slots=True)
class Trace:
    steps: List[str]
    digest: str = "0" * 32
    halt_reason: "HaltReason | None" = None
    finalized: bool = False
    contradictions: List[Contradiction] = field(default_factory=list)

    def add(self, label: str, quality: float, rels: int, ctx: int) -> None:
        entry = f"{len(self.steps)+1}:{label} q={quality:.2f} rel={rels} ctx={ctx}"
        self._record(entry)

    def add_contradiction(self, contradiction: Contradiction, isr: ISR) -> None:
        base = contradiction.base_label or "UNKNOWN"
        entry = (
            f"{len(self.steps)+1}:CONTRADICTION[{base}] "
            f"q={isr.quality:.2f} rel={len(isr.relations)} ctx={len(isr.context)}"
        )
        self.contradictions.append(contradiction)
        self._record(entry)

    def halt(self, reason: "HaltReason", isr: ISR, finalized: bool) -> None:
        self.halt_reason = reason
        self.finalized = finalized
        entry = (
            f"{len(self.steps)+1}:HALT[{reason.value}] "
            f"q={isr.quality:.2f} rel={len(isr.relations)} ctx={len(isr.context)}"
        )
        self._record(entry)

    def _record(self, entry: str) -> None:
        self.steps.append(entry)
        self.digest = blake2b((self.digest + entry).encode("utf-8"), digest_size=16).hexdigest()


class HaltReason(str, Enum):
    QUALITY_THRESHOLD = "QUALITY_THRESHOLD"
    SIGNATURE_REPEAT = "SIGNATURE_REPEAT"
    OPS_QUEUE_EMPTY = "OPS_QUEUE_EMPTY"
    MAX_STEPS = "MAX_STEPS"
    CONTRADICTION = "CONTRADICTION"


@dataclass(slots=True)
class RunOutcome:
    answer: str
    trace: Trace
    isr: ISR
    halt_reason: HaltReason
    finalized: bool
    equation: EquationSnapshot

    @property
    def quality(self) -> float:
        return self.isr.quality

    def has_answer(self) -> bool:
        return _get_answer_field(self.isr) is not None

    def meets_quality(self, min_quality: float) -> bool:
        return self.has_answer() and self.quality >= min_quality


def run_text(text: str, session: SessionCtx | None = None) -> Tuple[str, Trace]:
    outcome = run_text_full(text, session=session)
    return outcome.answer, outcome.trace


def run_text_full(text: str, session: SessionCtx | None = None) -> RunOutcome:
    session = session or SessionCtx()
    lexicon = session.lexicon
    if not (lexicon.synonyms or lexicon.pos_hint or lexicon.qualifiers or lexicon.rel_words):
        lexicon = DEFAULT_LEXICON
    tokens = tokenize(text, lexicon)
    struct0 = build_struct(tokens)
    return run_struct_full(struct0, session)


def run_struct(struct_node: Node, session: SessionCtx) -> Tuple[str, Trace]:
    outcome = run_struct_full(struct_node, session)
    return outcome.answer, outcome.trace


def run_struct_full(struct_node: Node, session: SessionCtx) -> RunOutcome:
    isr = initial_isr(struct_node, session)
    trace = Trace(steps=[])
    steps = 0
    seen_signatures = set()
    idle_loops = 0
    halt_reason: HaltReason | None = None
    finalized = False
    while steps < session.config.max_steps:
        steps += 1
        if not isr.ops_queue:
            if isr.answer.fields:
                if isr.quality < session.config.min_quality:
                    isr, delta = _finalize_convergence(isr, session, trace)
                    finalized = finalized or delta
                halt_reason = HaltReason.OPS_QUEUE_EMPTY
                break
            if isr.goals:
                isr.ops_queue.append(isr.goals[0])
            else:
                isr.ops_queue.extend([operation("ALIGN"), operation("STABILIZE"), operation("SUMMARIZE")])
        op = isr.ops_queue.popleft()
        isr = apply_operator(isr, op, session)
        trace.add(op.label or "NOOP", isr.quality, len(isr.relations), len(isr.context))
        if session.config.enable_contradiction_check:
            contradictions = detect_contradictions((*isr.ontology, *isr.relations, *isr.context))
            if contradictions:
                for contradiction in contradictions:
                    trace.add_contradiction(contradiction, isr)
                halt_reason = HaltReason.CONTRADICTION
                break
        signature = _state_signature(isr)
        if signature in seen_signatures:
            idle_loops += 1
            if idle_loops >= 2:
                if not isr.answer.fields or isr.quality < session.config.min_quality:
                    isr, delta = _finalize_convergence(isr, session, trace)
                    finalized = finalized or delta
                halt_reason = HaltReason.SIGNATURE_REPEAT
                break
        else:
            seen_signatures.add(signature)
            idle_loops = 0
        if isr.answer.fields and isr.quality >= session.config.min_quality:
            halt_reason = HaltReason.QUALITY_THRESHOLD
            break
    if halt_reason is None:
        halt_reason = HaltReason.MAX_STEPS
        if not isr.answer.fields or isr.quality < session.config.min_quality:
            isr, delta = _finalize_convergence(isr, session, trace)
            finalized = finalized or delta
    trace.halt(halt_reason, isr, finalized)
    answer_text = _answer_text(isr)
    return RunOutcome(
        answer=answer_text,
        trace=trace,
        isr=isr,
        halt_reason=halt_reason,
        finalized=finalized,
        equation=snapshot_equation(struct_node, isr),
    )


def _state_signature(isr: ISR) -> str:
    payload = "|".join(
        (
            f"rels:{_nodes_digest(isr.relations)}",
            f"ctx:{_nodes_digest(isr.context)}",
            f"goals:{_nodes_digest(isr.goals)}",
            f"ops:{_nodes_digest(isr.ops_queue)}",
            f"ans:{fingerprint(isr.answer)}",
            f"q:{isr.quality:.4f}",
        )
    )
    return blake2b(payload.encode("utf-8"), digest_size=12).hexdigest()


def _nodes_digest(nodes: Iterable[Node]) -> str:
    items = tuple(nodes)
    if not items:
        return "-"
    hasher = blake2b(digest_size=12)
    for node in items:
        hasher.update(fingerprint(node).encode("utf-8"))
    return hasher.hexdigest()


def _finalize_convergence(isr: ISR, session: SessionCtx, trace: Trace) -> Tuple[ISR, bool]:
    current = isr
    applied = False
    if not current.answer.fields:
        current = _apply_and_trace(current, "SUMMARIZE", "SUMMARIZE*", session, trace)
        applied = True
    if current.quality < session.config.min_quality:
        current = _apply_and_trace(current, "STABILIZE", "STABILIZE*", session, trace)
        applied = True
    return current, applied


def _apply_and_trace(isr: ISR, op_name: str, label: str, session: SessionCtx, trace: Trace) -> ISR:
    updated = apply_operator(isr, operation(op_name), session)
    trace.add(label, updated.quality, len(updated.relations), len(updated.context))
    return updated


def _get_answer_field(isr: ISR) -> Node | None:
    return dict(isr.answer.fields).get("answer")


def _answer_text(isr: ISR) -> str:
    field = _get_answer_field(isr)
    label = field.label if field and field.label else None
    return label or "Não encontrei resposta."


__all__ = [
    "run_text",
    "run_struct",
    "run_text_full",
    "run_struct_full",
    "Trace",
    "HaltReason",
    "RunOutcome",
    "EquationSnapshot",
]
