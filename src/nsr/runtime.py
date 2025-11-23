"""
Orquestrador do NSR: LxU → PSE → loop Φ → resposta.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace as dc_replace
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
from .operators import apply_operator
from .state import ISR, SessionCtx, initial_isr
from .explain import render_explanation
from .logic_persistence import deserialize_logic_engine, serialize_logic_engine
from .meta_transformer import MetaTransformer, MetaTransformResult, MetaCalculationPlan, MetaRoute, build_meta_summary
from .meta_calculator import MetaCalculationResult, execute_meta_plan
from .meta_calculus_router import text_operation_pipeline


def _ensure_logic_engine(session: SessionCtx):
    if session.logic_engine is None and session.logic_serialized:
        session.logic_engine = deserialize_logic_engine(session.logic_serialized)
    return session.logic_engine


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
    PLAN_EXECUTED = "PLAN_EXECUTED"


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
    meta_summary: Tuple[Node, ...] | None = None
    calc_plan: MetaCalculationPlan | None = None
    calc_result: MetaCalculationResult | None = None
    lc_meta: Node | None = None
    language_profile: Node | None = None
    code_ast: Node | None = None
    code_summary: Node | None = None
    math_ast: Node | None = None

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
    _ensure_logic_engine(session)
    transformer = MetaTransformer(session)
    meta = transformer.transform(text)
    calc_mode = getattr(session.config, "calc_mode", "hybrid")
    if calc_mode == "plan_only":
        plan_outcome = _run_plan_only(meta, session)
        if plan_outcome is not None:
            return plan_outcome
    struct0 = meta.struct_node
    return run_struct_full(
        struct0,
        session,
        preseed_answer=meta.preseed_answer,
        preseed_context=meta.preseed_context,
        preseed_quality=meta.preseed_quality,
        trace_hint=meta.trace_label,
        meta_info=meta,
    )


def run_struct(
    struct_node: Node,
    session: SessionCtx,
    preseed_answer: Node | None = None,
    preseed_context: Tuple[Node, ...] | None = None,
    preseed_quality: float | None = None,
) -> Tuple[str, Trace]:
    outcome = run_struct_full(
        struct_node,
        session,
        preseed_answer=preseed_answer,
        preseed_context=preseed_context,
        preseed_quality=preseed_quality,
    )
    return outcome.answer, outcome.trace


def run_struct_full(
    struct_node: Node,
    session: SessionCtx,
    preseed_answer: Node | None = None,
    preseed_context: Tuple[Node, ...] | None = None,
    preseed_quality: float | None = None,
    trace_hint: str | None = None,
    meta_info: MetaTransformResult | None = None,
) -> RunOutcome:
    isr = initial_isr(struct_node, session)
    if preseed_answer is not None:
        isr.answer = preseed_answer
    if preseed_context:
        isr.context = tuple((*isr.context, *preseed_context))
    if preseed_quality is not None:
        isr.quality = preseed_quality
    plan_label = _prime_ops_from_meta_calc(isr, struct_node, meta_info)
    trace = Trace(steps=[])
    if trace_hint:
        trace.add(trace_hint, isr.quality, len(isr.relations), len(isr.context))
    if plan_label:
        trace.add(plan_label, isr.quality, len(isr.relations), len(isr.context))
    isr, code_label = _apply_code_rewrite_if_needed(isr, session, meta_info)
    if code_label:
        trace.add(code_label, isr.quality, len(isr.relations), len(isr.context))
    calc_mode = getattr(session.config, "calc_mode", "hybrid")
    plan_exec_enabled = calc_mode != "skip"
    if preseed_answer is not None and isr.quality >= session.config.min_quality:
        trace.halt(HaltReason.QUALITY_THRESHOLD, isr, finalized=True)
        calc_plan = meta_info.calc_plan if meta_info else None
        calc_result = (
            execute_meta_plan(
                calc_plan,
                struct_node,
                session,
                code_summary=meta_info.code_summary if meta_info else None,
            )
            if (calc_plan and plan_exec_enabled)
            else None
        )
        calc_result = _validate_calc_result(calc_result, isr, trace)
        _maybe_attach_calc_answer(isr, calc_result, meta_info)
        snapshot = snapshot_equation(struct_node, isr)
        summary = (
            build_meta_summary(
                meta_info,
                _answer_text(isr),
                isr.quality,
                HaltReason.QUALITY_THRESHOLD.value,
                calc_result,
            )
            if meta_info
            else None
        )
        return RunOutcome(
            answer=_answer_text(isr),
            trace=trace,
            isr=isr,
            halt_reason=HaltReason.QUALITY_THRESHOLD,
            finalized=True,
            equation=snapshot,
            equation_digest=snapshot.digest(),
            explanation=render_explanation(isr, struct_node),
            meta_summary=summary,
            calc_plan=calc_plan,
            calc_result=calc_result,
            lc_meta=meta_info.lc_meta if meta_info else None,
            language_profile=meta_info.language_profile if meta_info else None,
            code_ast=meta_info.code_ast if meta_info else None,
            code_summary=meta_info.code_summary if meta_info else None,
            math_ast=meta_info.math_ast if meta_info else None,
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
    if session.logic_engine:
        session.logic_serialized = serialize_logic_engine(session.logic_engine)
    calc_plan = meta_info.calc_plan if meta_info else None
    calc_result = (
        execute_meta_plan(
            calc_plan,
            struct_node,
            session,
            code_summary=meta_info.code_summary if meta_info else None,
        )
        if (calc_plan and plan_exec_enabled)
        else None
    )
    calc_result = _validate_calc_result(calc_result, isr, trace)
    context_updated = _maybe_attach_calc_answer(isr, calc_result, meta_info)
    if context_updated:
        last_snapshot = None
    snapshot = last_snapshot if last_snapshot is not None else snapshot_equation(struct_node, isr)
    meta_summary = (
        build_meta_summary(meta_info, answer_text, isr.quality, halt_reason.value, calc_result) if meta_info else None
    )
    if meta_summary is not None:
        session.meta_history.append(meta_summary)
        limit = getattr(session.config, "meta_history_limit", 0)
        if limit and len(session.meta_history) > limit:
            del session.meta_history[:-limit]
    return RunOutcome(
        answer=answer_text,
        trace=trace,
        isr=isr,
        halt_reason=halt_reason,
        finalized=finalized,
        equation=snapshot,
        equation_digest=snapshot.digest(),
        explanation=render_explanation(isr, struct_node),
        meta_summary=meta_summary,
        calc_plan=calc_plan,
        calc_result=calc_result,
        lc_meta=meta_info.lc_meta if meta_info else None,
        language_profile=meta_info.language_profile if meta_info else None,
        code_ast=meta_info.code_ast if meta_info else None,
        code_summary=meta_info.code_summary if meta_info else None,
        math_ast=meta_info.math_ast if meta_info else None,
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


def _validate_calc_result(
    calc_result: MetaCalculationResult | None,
    isr: ISR,
    trace: Trace,
) -> MetaCalculationResult | None:
    if calc_result is None:
        return None
    if calc_result.answer is None or not isr.answer.fields:
        return calc_result
    if calc_result.plan.route is MetaRoute.TEXT:
        return calc_result
    expected = fingerprint(isr.answer)
    actual = fingerprint(calc_result.answer)
    if expected == actual:
        return calc_result
    trace.invariant_failures.append(
        f"CALC_PLAN_MISMATCH q={isr.quality:.2f} expected={expected} actual={actual}"
    )
    updated_error = calc_result.error or "calc_plan_mismatch"
    return dc_replace(calc_result, error=updated_error, consistent=False)


def _maybe_attach_calc_answer(
    isr: ISR,
    calc_result: MetaCalculationResult | None,
    meta_info: MetaTransformResult | None,
) -> bool:
    if (
        calc_result is None
        or calc_result.answer is None
        or meta_info is None
        or meta_info.route is not MetaRoute.TEXT
    ):
        return False
    answer = calc_result.answer
    existing = {fingerprint(node) for node in isr.context}
    sig = fingerprint(answer)
    if sig in existing:
        return False
    isr.context = tuple((*isr.context, answer))
    return True


def _prime_ops_from_meta_calc(
    isr: ISR,
    struct_node: Node,
    meta_info: MetaTransformResult | None,
) -> str | None:
    if meta_info is None or meta_info.meta_calculation is None:
        return None
    pipeline_ops = text_operation_pipeline(meta_info.meta_calculation, struct_node)
    if not pipeline_ops:
        return None
    original_ops = tuple(isr.ops_queue)
    isr.ops_queue.clear()
    isr.ops_queue.extend(pipeline_ops)
    isr.ops_queue.extend(original_ops)
    operator = (meta_info.meta_calculation.operator or "text").upper()
    chain = "→".join(filter(None, (op.label or "" for op in pipeline_ops)))
    return f"Φ_PLAN[{operator}:{chain}]"


def _apply_code_rewrite_if_needed(
    isr: ISR,
    session: SessionCtx,
    meta_info: MetaTransformResult | None,
) -> tuple[ISR, str | None]:
    if meta_info is None or meta_info.code_ast is None:
        return isr, None
    updated = apply_operator(isr, operation("REWRITE_CODE"), session)
    return updated, "Φ_CODE[REWRITE_CODE]"


def _run_plan_only(meta: MetaTransformResult, session: SessionCtx) -> RunOutcome | None:
    plan = meta.calc_plan
    if plan is None:
        return None
    calc_result = execute_meta_plan(plan, meta.struct_node, session, code_summary=meta.code_summary)
    if calc_result.answer is None:
        return None
    isr = initial_isr(meta.struct_node, session)
    if meta.preseed_context:
        isr.context = tuple((*isr.context, *meta.preseed_context))
    isr.answer = calc_result.answer
    isr.quality = meta.preseed_quality or session.config.min_quality
    trace = Trace(steps=[])
    trace_label = f"PLAN_ONLY[{meta.route.value.upper()}]"
    trace.add(trace_label, isr.quality, len(isr.relations), len(isr.context))
    calc_result = _validate_calc_result(calc_result, isr, trace)
    _maybe_attach_calc_answer(isr, calc_result, meta)
    trace.halt(HaltReason.PLAN_EXECUTED, isr, finalized=True)
    snapshot = snapshot_equation(meta.struct_node, isr)
    answer_text = _answer_text(isr)
    meta_summary = build_meta_summary(meta, answer_text, isr.quality, HaltReason.PLAN_EXECUTED.value, calc_result)
    session.meta_history.append(meta_summary)
    limit = getattr(session.config, "meta_history_limit", 0)
    if limit and len(session.meta_history) > limit:
        del session.meta_history[:-limit]
    return RunOutcome(
        answer=answer_text,
        trace=trace,
        isr=isr,
        halt_reason=HaltReason.PLAN_EXECUTED,
        finalized=True,
        equation=snapshot,
        equation_digest=snapshot.digest(),
        explanation=render_explanation(isr, meta.struct_node),
        meta_summary=meta_summary,
        calc_plan=plan,
        calc_result=calc_result,
        lc_meta=meta.lc_meta,
        language_profile=meta.language_profile,
        code_ast=meta.code_ast,
        code_summary=meta.code_summary,
        math_ast=meta.math_ast,
    )


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
