"""
Orquestrador do NSR: LxU → PSE → loop Φ → resposta.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from hashlib import blake2b
from typing import Iterable, List, Tuple, Optional

from liu import Node, operation, fingerprint

from .consistency import Contradiction, detect_contradictions
from .equation import (
    EquationInvariantStatus,
    EquationSnapshot,
    EquationSnapshotStats,
    snapshot_equation,
)
from .lex import tokenize, DEFAULT_LEXICON
from .operators import apply_operator
from .parser import build_struct
from .state import ISR, SessionCtx, initial_isr
from .explain import render_explanation
from .ian_bridge import maybe_route_text


@dataclass(slots=True)
class Trace:
    steps: List[str]
    digest: str = "0" * 32
    halt_reason: "HaltReason | None" = None
    finalized: bool = False
    contradictions: List[Contradiction] = field(default_factory=list)
    invariant_failures: List[str] = field(default_factory=list)

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

    def add_invariant_failure(
        self,
        label: str,
        status: EquationInvariantStatus,
        stats: EquationSnapshotStats,
    ) -> None:
        entry = (
            f"{len(self.steps)}:INV[{label}] "
            f"delta={status.quality_delta:.4f} "
            f"failures={','.join(status.failures)} "
            f"digest={stats.equation_digest}"
        )
        self.invariant_failures.append(entry)

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
    INVARIANT_FAILURE = "INVARIANT_FAILURE"


@dataclass(slots=True)
class RunOutcome:
    answer: str
    trace: Trace
    isr: ISR
    halt_reason: HaltReason
    finalized: bool
    equation: EquationSnapshot
    equation_digest: str
    explanation: str

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


def run_text_with_explanation(
    text: str, session: SessionCtx | None = None
) -> Tuple[str, Trace, str]:
    """
    Variante determinística que retorna texto, trace e narrativa da equação.
    """

    outcome = run_text_full(text, session=session)
    return outcome.answer, outcome.trace, outcome.explanation


def run_text_full(text: str, session: SessionCtx | None = None) -> RunOutcome:
    session = session or SessionCtx()
    lexicon = session.lexicon
    if not (lexicon.synonyms or lexicon.pos_hint or lexicon.qualifiers or lexicon.rel_words):
        lexicon = DEFAULT_LEXICON
    instinct_hook = maybe_route_text(text)
    if instinct_hook:
        struct0 = instinct_hook.struct_node
        preseed_answer = instinct_hook.answer_node
        trace_hint = f"IAN[{instinct_hook.utterance.role}]"
        preseed_context = instinct_hook.context_nodes
        preseed_quality = instinct_hook.quality
        preseed_relations = instinct_hook.relation_nodes
    else:
        tokens = tokenize(text, lexicon)
        struct0 = build_struct(tokens)
        preseed_answer = None
        trace_hint = None
        preseed_context = None
        preseed_quality = None
        preseed_relations = None
    return run_struct_full(
        struct0,
        session,
        preseed_answer=preseed_answer,
        preseed_context=preseed_context,
        preseed_quality=preseed_quality,
        preseed_relations=preseed_relations,
        trace_hint=trace_hint,
    )


def run_struct(
    struct_node: Node,
    session: SessionCtx,
    preseed_answer: Node | None = None,
    preseed_context: Tuple[Node, ...] | None = None,
    preseed_quality: float | None = None,
    preseed_relations: Tuple[Node, ...] | None = None,
) -> Tuple[str, Trace]:
    outcome = run_struct_full(
        struct_node,
        session,
        preseed_answer=preseed_answer,
        preseed_context=preseed_context,
        preseed_quality=preseed_quality,
        preseed_relations=preseed_relations,
    )
    return outcome.answer, outcome.trace


def run_struct_full(
    struct_node: Node,
    session: SessionCtx,
    preseed_answer: Node | None = None,
    preseed_context: Tuple[Node, ...] | None = None,
    preseed_quality: float | None = None,
    preseed_relations: Tuple[Node, ...] | None = None,
    trace_hint: str | None = None,
) -> RunOutcome:
    isr = initial_isr(struct_node, session)
    if preseed_answer is not None:
        isr.answer = preseed_answer
    if preseed_context:
        isr.context = tuple((*isr.context, *preseed_context))
    if preseed_relations:
        isr.relations = tuple((*isr.relations, *preseed_relations))
    if preseed_quality is not None:
        isr.quality = preseed_quality
    trace = Trace(steps=[])
    if trace_hint:
        trace.add(trace_hint, isr.quality, len(isr.relations), len(isr.context))
    if preseed_answer is not None and isr.quality >= session.config.min_quality:
        trace.halt(HaltReason.QUALITY_THRESHOLD, isr, finalized=True)
        snapshot = snapshot_equation(struct_node, isr)
        return RunOutcome(
            answer=_answer_text(isr),
            trace=trace,
            isr=isr,
            halt_reason=HaltReason.QUALITY_THRESHOLD,
            finalized=True,
            equation=snapshot,
            equation_digest=snapshot.digest(),
            explanation=render_explanation(isr, struct_node),
        )
    steps = 0
    seen_signatures = set()
    idle_loops = 0
    halt_reason: HaltReason | None = None
    finalized = False
    last_snapshot: Optional[EquationSnapshot] = None
    last_stats: Optional[EquationSnapshotStats] = None
    while steps < session.config.max_steps:
        steps += 1
        if not isr.ops_queue:
            if isr.answer.fields:
                if isr.quality < session.config.min_quality:
                    isr, delta, snap_update, stats_update, status = _finalize_convergence(
                        isr, session, trace, struct_node, last_stats
                    )
                    if snap_update is not None:
                        last_snapshot = snap_update
                    if stats_update is not None:
                        last_stats = stats_update
                    finalized = finalized or delta
                    if status is not None and not status.ok:
                        halt_reason = HaltReason.INVARIANT_FAILURE
                        break
                halt_reason = HaltReason.OPS_QUEUE_EMPTY
                break
            if isr.goals:
                isr.ops_queue.append(isr.goals[0])
            else:
                isr.ops_queue.extend([operation("ALIGN"), operation("STABILIZE"), operation("SUMMARIZE")])
        op = isr.ops_queue.popleft()
        op_label = op.label or "NOOP"
        isr = apply_operator(isr, op, session)
        trace.add(op_label, isr.quality, len(isr.relations), len(isr.context))
        snapshot_step, stats_step, invariant_status = _audit_state(
            struct_node, isr, trace, last_stats, op_label
        )
        last_snapshot = snapshot_step
        last_stats = stats_step
        if not invariant_status.ok:
            halt_reason = HaltReason.INVARIANT_FAILURE
            break
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
                    isr, delta, snap_update, stats_update, status = _finalize_convergence(
                        isr, session, trace, struct_node, last_stats
                    )
                    if snap_update is not None:
                        last_snapshot = snap_update
                    if stats_update is not None:
                        last_stats = stats_update
                    finalized = finalized or delta
                    if status is not None and not status.ok:
                        halt_reason = HaltReason.INVARIANT_FAILURE
                        break
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
            isr, delta, snap_update, stats_update, status = _finalize_convergence(
                isr, session, trace, struct_node, last_stats
            )
            if snap_update is not None:
                last_snapshot = snap_update
            if stats_update is not None:
                last_stats = stats_update
            finalized = finalized or delta
            if status is not None and not status.ok:
                halt_reason = HaltReason.INVARIANT_FAILURE
    trace.halt(halt_reason, isr, finalized)
    answer_text = _answer_text(isr)
    snapshot = last_snapshot if last_snapshot is not None else snapshot_equation(struct_node, isr)
    return RunOutcome(
        answer=answer_text,
        trace=trace,
        isr=isr,
        halt_reason=halt_reason,
        finalized=finalized,
        equation=snapshot,
        equation_digest=snapshot.digest(),
        explanation=render_explanation(isr, struct_node),
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


def _audit_state(
    struct_node: Node,
    isr: ISR,
    trace: Trace,
    previous_stats: Optional[EquationSnapshotStats],
    label: str,
) -> Tuple[EquationSnapshot, EquationSnapshotStats, EquationInvariantStatus]:
    snapshot = snapshot_equation(struct_node, isr)
    stats = snapshot.stats()
    status = stats.validate(previous=previous_stats)
    if not status.ok:
        trace.add_invariant_failure(label, status, stats)
    return snapshot, stats, status


def _finalize_convergence(
    isr: ISR,
    session: SessionCtx,
    trace: Trace,
    struct_node: Node,
    previous_stats: Optional[EquationSnapshotStats],
) -> Tuple[
    ISR,
    bool,
    Optional[EquationSnapshot],
    Optional[EquationSnapshotStats],
    Optional[EquationInvariantStatus],
]:
    current = isr
    applied = False
    last_snapshot: Optional[EquationSnapshot] = None
    last_stats = previous_stats
    last_status: Optional[EquationInvariantStatus] = None
    if not current.answer.fields:
        current, last_snapshot, last_stats, last_status = _apply_and_trace(
            current,
            "SUMMARIZE",
            "SUMMARIZE*",
            session,
            trace,
            struct_node,
            last_stats,
        )
        applied = True
        if last_status is not None and not last_status.ok:
            return current, applied, last_snapshot, last_stats, last_status
    if current.quality < session.config.min_quality:
        current, last_snapshot, last_stats, last_status = _apply_and_trace(
            current,
            "STABILIZE",
            "STABILIZE*",
            session,
            trace,
            struct_node,
            last_stats,
        )
        applied = True
    return current, applied, last_snapshot, last_stats, last_status


def _apply_and_trace(
    isr: ISR,
    op_name: str,
    label: str,
    session: SessionCtx,
    trace: Trace,
    struct_node: Node,
    previous_stats: Optional[EquationSnapshotStats],
) -> Tuple[ISR, EquationSnapshot, EquationSnapshotStats, EquationInvariantStatus]:
    updated = apply_operator(isr, operation(op_name), session)
    trace.add(label, updated.quality, len(updated.relations), len(updated.context))
    snapshot, stats, status = _audit_state(struct_node, updated, trace, previous_stats, label)
    return updated, snapshot, stats, status


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
    "EquationSnapshotStats",
    "EquationInvariantStatus",
]
