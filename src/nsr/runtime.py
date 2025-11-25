"""
Orquestrador do NSR: LxU → PSE → loop Φ → resposta.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace as dc_replace
from enum import Enum
from hashlib import blake2b
from typing import Iterable, List, Tuple, Optional
from collections import deque, Counter

from liu import Node, NodeKind, operation, fingerprint, text

from .consistency import Contradiction, detect_contradictions
from .equation import (
    EquationInvariantStatus,
    EquationSnapshot,
    EquationSnapshotStats,
    snapshot_equation,
)
from .operators import (
    apply_operator,
    _latest_tagged_struct,
    _latest_unsynthesized_plan,
    _latest_unsynthesized_proof,
    _latest_unsynthesized_prog,
)
from .state import ISR, SessionCtx, initial_isr
from .explain import render_explanation
from .logic_persistence import deserialize_logic_engine, serialize_logic_engine
from .meta_transformer import MetaTransformer, MetaTransformResult, MetaCalculationPlan, MetaRoute, build_meta_summary
from .meta_calculator import MetaCalculationResult, execute_meta_plan
from .meta_calculus_router import text_operation_pipeline
from .meta_reasoner import build_meta_reasoning
from .meta_reflection import build_meta_reflection
from .meta_justification import build_meta_justification
from .meta_expressor import build_meta_expression
from .meta_memory import build_meta_memory
from .meta_equation import build_meta_equation_node
from .meta_memory_store import append_memory, load_recent_memory
from .meta_memory_induction import record_episode, run_memory_induction
from .context_stats import build_context_probabilities
from .meta_synthesis import build_meta_synthesis


# Maximum iterations for synthesis drain loop
MAX_SYNTHESIS_DRAIN_ITERATIONS = 6


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
    meta_reasoning: Node | None = None
    meta_reflection: Node | None = None
    meta_justification: Node | None = None
    meta_expression: Node | None = None
    meta_memory: Node | None = None
    meta_synthesis: Node | None = None
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
    _ensure_memory_loaded(session)
    transformer = MetaTransformer(session)
    meta = transformer.transform(text)
    if session.meta_buffer:
        extra_context = tuple(
            operation("MEMORY_RECALL", buffer_node)
            if buffer_node is not None
            else operation("MEMORY_RECALL")
            for buffer_node in session.meta_buffer
        )
        if meta.preseed_context:
            meta_context = tuple((*meta.preseed_context, *extra_context))
        else:
            meta_context = extra_context
        meta = MetaTransformResult(
            struct_node=meta.struct_node,
            route=meta.route,
            input_text=meta.input_text,
            trace_label=meta.trace_label,
            preseed_answer=meta.preseed_answer,
            preseed_context=meta_context,
            preseed_quality=meta.preseed_quality,
            language_hint=meta.language_hint,
            calc_plan=meta.calc_plan,
            lc_meta=meta.lc_meta,
            meta_calculation=meta.meta_calculation,
            phi_plan_ops=meta.phi_plan_ops,
            language_profile=meta.language_profile,
            code_ast=meta.code_ast,
            code_summary=meta.code_summary,
            math_ast=meta.math_ast,
            plan_goal=meta.plan_goal,
        )
    calc_mode = getattr(session.config, "calc_mode", "hybrid")
    if calc_mode == "plan_only":
        plan_outcome = _run_plan_only(meta, session)
        if plan_outcome is not None:
            return _finalize_outcome(session, text, plan_outcome)
    struct0 = meta.struct_node
    outcome = run_struct_full(
        struct0,
        session,
        preseed_answer=meta.preseed_answer,
        preseed_context=meta.preseed_context,
        preseed_quality=meta.preseed_quality,
        trace_hint=meta.trace_label,
        meta_info=meta,
    )
    return _finalize_outcome(session, text, outcome)


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
    logic_proof_node: Node | None = None
    if trace_hint:
        trace.add(trace_hint, isr.quality, len(isr.relations), len(isr.context))
    if plan_label:
        trace.add(plan_label, isr.quality, len(isr.relations), len(isr.context))
    isr, code_label = _apply_code_rewrite_if_needed(isr, session, meta_info)
    if code_label:
        trace.add(code_label, isr.quality, len(isr.relations), len(isr.context))
    isr = _apply_memory_recall_if_needed(isr, session, trace)
    isr = _apply_memory_link_if_needed(isr, session, trace)
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
        reasoning_node = build_meta_reasoning(trace.steps)
        reflection_node = build_meta_reflection(reasoning_node)
        justification_node = build_meta_justification(reasoning_node)
        isr = _apply_trace_summary_if_needed(isr, session, reasoning_node, trace)
        isr = _apply_reflection_summary_if_needed(isr, session, reflection_node, trace)
        isr = _drain_synthesis_ops(isr, session)
        language = _resolve_language(meta_info, session)
        memory_refs = tuple(node for node in session.meta_buffer if node is not None)
        if (
            meta_info
            and meta_info.route is MetaRoute.LOGIC
            and (meta_info.trace_label or "").startswith("LOGIC[QUERY")
        ):
            isr = apply_operator(isr, operation("PROVE", meta_info.struct_node), session)
            isr = _drain_synthesis_ops(isr, session)
            logic_proof_node = _latest_logic_proof(isr.context)
        meta_expression = build_meta_expression(
            isr.answer,
            reasoning=reasoning_node,
            reflection=reflection_node,
            quality=isr.quality,
            halt_reason=HaltReason.QUALITY_THRESHOLD.value,
            route=meta_info.route if meta_info else None,
            language=language,
            memory_refs=memory_refs,
        )
        answer_text = _answer_text(isr)
        equation_node = (
            build_meta_equation_node(snapshot, session.last_equation_stats)
            if meta_info
            else None
        )
        context_prob_node = build_context_probabilities(isr)
        synthesis_node = build_meta_synthesis(isr.context)
        equation_stats = snapshot.stats()
        memory_entry = _memory_entry_payload(
            meta_info,
            answer_text,
            meta_expression,
            reasoning_node,
            reflection_node,
            justification_node,
            equation_node,
            logic_proof_node,
            synthesis_node,
        )
        meta_memory = build_meta_memory(session.meta_history, memory_entry)
        summary = (
            build_meta_summary(
                meta_info,
                answer_text,
                isr.quality,
                HaltReason.QUALITY_THRESHOLD.value,
                calc_result,
                meta_reasoning=reasoning_node,
                meta_reflection=reflection_node,
                meta_justification=justification_node,
                meta_expression=meta_expression,
                meta_memory=meta_memory,
                meta_equation=equation_node,
                meta_proof=logic_proof_node,
                meta_context_prob=context_prob_node,
                meta_synthesis=synthesis_node,
            )
            if meta_info
            else None
        )
        session.meta_buffer = (
            tuple(meta_ctx for meta_ctx in session.meta_buffer if meta_ctx is not None) + ((meta_memory,) if meta_memory else tuple())
        )
        _persist_meta_memory(session, meta_memory)
        session.last_equation_stats = equation_stats
        outcome = RunOutcome(
            answer=answer_text,
            trace=trace,
            isr=isr,
            halt_reason=HaltReason.QUALITY_THRESHOLD,
            finalized=True,
            equation=snapshot,
            equation_digest=snapshot.digest(),
            explanation=render_explanation(isr, struct_node),
            meta_summary=summary,
            meta_reasoning=reasoning_node if meta_info else None,
            meta_reflection=reflection_node if meta_info else None,
            meta_justification=justification_node if meta_info else None,
            meta_expression=meta_expression,
            meta_memory=meta_memory,
            meta_synthesis=synthesis_node,
            calc_plan=calc_plan,
            calc_result=calc_result,
            lc_meta=meta_info.lc_meta if meta_info else None,
            language_profile=meta_info.language_profile if meta_info else None,
            code_ast=meta_info.code_ast if meta_info else None,
            code_summary=meta_info.code_summary if meta_info else None,
            math_ast=meta_info.math_ast if meta_info else None,
        )
        return outcome
    steps = 0
    seen_signatures = set()
    idle_loops = 0
    halt_reason: HaltReason | None = None
    finalized = False
    last_snapshot: Optional[EquationSnapshot] = None
    last_stats: Optional[EquationSnapshotStats] = None
    while steps < session.config.max_steps:
        steps += 1
        _maybe_queue_synthesis_ops(isr)
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
                _prioritize_ops_queue(isr)
            else:
                isr.ops_queue.extend([operation("ALIGN"), operation("STABILIZE"), operation("SUMMARIZE")])
                _prioritize_ops_queue(isr)
        op = isr.ops_queue.popleft()
        op_label = op.label or "NOOP"
        isr = apply_operator(isr, op, session)
        label_for_trace = op_label
        if op_label.upper() == "NORMALIZE":
            label_for_trace = _format_normalize_trace_label(op_label, isr.context)
        trace.add(label_for_trace, isr.quality, len(isr.relations), len(isr.context))
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
        _maybe_queue_synthesis_ops(isr)
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
            if _latest_unsynthesized_plan(isr.context) or _latest_unsynthesized_proof(isr.context):
                _maybe_queue_synthesis_ops(isr)
                continue
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
    if (
        meta_info
        and meta_info.route is MetaRoute.LOGIC
        and (meta_info.trace_label or "").startswith("LOGIC[QUERY")
    ):
        isr = apply_operator(isr, operation("PROVE", meta_info.struct_node), session)
        isr = _drain_synthesis_ops(isr, session)
        logic_proof_node = _latest_logic_proof(isr.context)
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
    reasoning_node = build_meta_reasoning(trace.steps)
    reflection_node = build_meta_reflection(reasoning_node)
    justification_node = build_meta_justification(reasoning_node)
    isr = _apply_trace_summary_if_needed(isr, session, reasoning_node, trace)
    isr = _apply_reflection_summary_if_needed(isr, session, reflection_node, trace)
    isr = _drain_synthesis_ops(isr, session)
    language = _resolve_language(meta_info, session)
    memory_refs = tuple(node for node in session.meta_buffer if node is not None)
    meta_expression = build_meta_expression(
        isr.answer,
        reasoning=reasoning_node,
        reflection=reflection_node,
        quality=isr.quality,
        halt_reason=halt_reason.value,
        route=meta_info.route if meta_info else None,
        language=language,
        memory_refs=memory_refs,
    )
    equation_node = (
        build_meta_equation_node(snapshot, session.last_equation_stats)
        if meta_info
        else None
    )
    context_prob_node = build_context_probabilities(isr)
    synthesis_node = build_meta_synthesis(isr.context)
    equation_stats = snapshot.stats()
    memory_entry = _memory_entry_payload(
        meta_info,
        answer_text,
        meta_expression,
        reasoning_node,
        reflection_node,
        justification_node,
        equation_node,
        logic_proof_node,
        synthesis_node,
    )
    meta_memory = build_meta_memory(session.meta_history, memory_entry)
    meta_summary = (
        build_meta_summary(
            meta_info,
            answer_text,
            isr.quality,
            halt_reason.value,
            calc_result,
            meta_reasoning=reasoning_node,
            meta_reflection=reflection_node,
            meta_justification=justification_node,
            meta_expression=meta_expression,
            meta_memory=meta_memory,
            meta_equation=equation_node,
            meta_proof=logic_proof_node,
            meta_context_prob=context_prob_node,
            meta_synthesis=synthesis_node,
        )
        if meta_info
        else None
    )
    session.meta_buffer = (
        tuple(meta_ctx for meta_ctx in session.meta_buffer if meta_ctx is not None) + ((meta_memory,) if meta_memory else tuple())
    )
    _persist_meta_memory(session, meta_memory)
    session.last_equation_stats = equation_stats
    if meta_summary is not None:
        session.meta_history.append(meta_summary)
        limit = getattr(session.config, "meta_history_limit", 0)
        if limit and len(session.meta_history) > limit:
            del session.meta_history[:-limit]
    outcome = RunOutcome(
        answer=answer_text,
        trace=trace,
        isr=isr,
        halt_reason=halt_reason,
        finalized=finalized,
        equation=snapshot,
        equation_digest=snapshot.digest(),
        explanation=render_explanation(isr, struct_node),
        meta_summary=meta_summary,
        meta_reasoning=reasoning_node if meta_info else None,
        meta_reflection=reflection_node if meta_info else None,
        meta_justification=justification_node if meta_info else None,
        meta_expression=meta_expression,
        meta_memory=meta_memory,
        meta_synthesis=synthesis_node,
        calc_plan=calc_plan,
        calc_result=calc_result,
        lc_meta=meta_info.lc_meta if meta_info else None,
        language_profile=meta_info.language_profile if meta_info else None,
        code_ast=meta_info.code_ast if meta_info else None,
        code_summary=meta_info.code_summary if meta_info else None,
        math_ast=meta_info.math_ast if meta_info else None,
    )
    return outcome


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
    if meta_info is None:
        return None
    pipeline_ops: list[Node] = []
    if meta_info.meta_calculation is not None:
        pipeline_ops = list(text_operation_pipeline(meta_info.meta_calculation, struct_node))
    if meta_info.plan_goal:
        pipeline_ops.insert(0, operation("PLAN_DECOMPOSE", text(meta_info.plan_goal)))
    if not pipeline_ops:
        return None
    original_ops = tuple(isr.ops_queue)
    isr.ops_queue.clear()
    isr.ops_queue.extend(pipeline_ops)
    isr.ops_queue.extend(original_ops)
    _prioritize_ops_queue(isr)
    operator = (
        (meta_info.meta_calculation.operator if meta_info.meta_calculation else "plan").upper()
    )
    chain = "→".join(filter(None, (op.label or "" for op in pipeline_ops)))
    return f"Φ_PLAN[{operator}:{chain}]"


def _prioritize_ops_queue(isr: ISR) -> None:
    priorities = _context_priority_map(isr)
    if not priorities or not isr.ops_queue:
        return
    indexed_ops = list(isr.ops_queue)
    indexed_ops = sorted(
        enumerate(indexed_ops),
        key=lambda item: (-priorities.get((item[1].label or "").upper(), 0.0), item[0]),
    )
    isr.ops_queue = deque(op for _, op in indexed_ops)


def _context_priority_map(isr: ISR) -> dict[str, float]:
    counts = Counter()
    for node in isr.context:
        label = _context_node_label(node)
        if label:
            counts[label] += 1
    total = sum(counts.values())
    if not total:
        return {}
    return {label: count / total for label, count in counts.items()}


def _context_node_label(node: Node) -> str:
    if node.kind is NodeKind.STRUCT:
        tag_field = dict(node.fields).get("tag")
        if tag_field and tag_field.label:
            return tag_field.label.upper()
    return (node.label or "").upper()


def _queue_contains_label(queue: deque[Node], label: str) -> bool:
    target = label.upper()
    for op in queue:
        if (op.label or "").upper() == target:
            return True
    return False


def _maybe_queue_synthesis_ops(isr: ISR) -> None:
    if _latest_unsynthesized_plan(isr.context) and not _queue_contains_label(isr.ops_queue, "SYNTH_PLAN"):
        isr.ops_queue.appendleft(operation("SYNTH_PLAN"))
    if _latest_unsynthesized_proof(isr.context) and not _queue_contains_label(isr.ops_queue, "SYNTH_PROOF"):
        isr.ops_queue.appendleft(operation("SYNTH_PROOF"))
    if _latest_unsynthesized_prog(isr.context) and not _queue_contains_label(isr.ops_queue, "SYNTH_PROG"):
        isr.ops_queue.appendleft(operation("SYNTH_PROG"))


def _drain_synthesis_ops(isr: ISR, session: SessionCtx) -> ISR:
    # Bounded loop to execute any pending synthesis operators outside do/while
    for _ in range(MAX_SYNTHESIS_DRAIN_ITERATIONS):
        pending_plan = _latest_unsynthesized_plan(isr.context)
        if pending_plan:
            isr = apply_operator(isr, operation("SYNTH_PLAN"), session)
            continue
        pending_proof = _latest_unsynthesized_proof(isr.context)
        if pending_proof:
            isr = apply_operator(isr, operation("SYNTH_PROOF"), session)
            continue
        pending_prog = _latest_unsynthesized_prog(isr.context)
        if pending_prog:
            isr = apply_operator(isr, operation("SYNTH_PROG"), session)
            continue
        break
    return isr


def _apply_code_rewrite_if_needed(
    isr: ISR,
    session: SessionCtx,
    meta_info: MetaTransformResult | None,
) -> tuple[ISR, str | None]:
    if meta_info is None or meta_info.code_ast is None:
        return isr, None
    updated = apply_operator(isr, operation("REWRITE_CODE"), session)
    return updated, "Φ_CODE[REWRITE_CODE]"


def _resolve_language(meta_info: MetaTransformResult | None, session: SessionCtx) -> str | None:
    if meta_info and meta_info.language_hint:
        return meta_info.language_hint
    return session.language_hint


def _apply_trace_summary_if_needed(
    isr: ISR,
    session: SessionCtx,
    reasoning_node: Node | None,
    trace: Trace,
) -> ISR:
    if reasoning_node is None:
        return isr
    updated = apply_operator(isr, operation("TRACE_SUMMARY", reasoning_node), session)
    trace.add("Φ_META[TRACE_SUMMARY]", updated.quality, len(updated.relations), len(updated.context))
    return updated


def _apply_reflection_summary_if_needed(
    isr: ISR,
    session: SessionCtx,
    reflection_node: Node | None,
    trace: Trace,
) -> ISR:
    if reflection_node is None:
        return isr
    updated = apply_operator(isr, operation("TRACE_REFLECTION", reflection_node), session)
    trace.add("Φ_META[TRACE_REFLECTION]", updated.quality, len(updated.relations), len(updated.context))
    return updated


def _apply_memory_recall_if_needed(isr: ISR, session: SessionCtx, trace: Trace) -> ISR:
    recall_ops = [
        node
        for node in isr.context
        if node.kind is NodeKind.OP and (node.label or "").upper() == "MEMORY_RECALL"
    ]
    if not recall_ops:
        return isr
    isr.context = tuple(
        node
        for node in isr.context
        if not (node.kind is NodeKind.OP and (node.label or "").upper() == "MEMORY_RECALL")
    )
    for op in recall_ops:
        payload = op.args[0] if op.args else None
        recall_node = operation("MEMORY_RECALL", payload) if payload is not None else operation("MEMORY_RECALL")
        isr = apply_operator(isr, recall_node, session)
        trace.add("Φ_MEMORY[RECALL]", isr.quality, len(isr.relations), len(isr.context))
    return isr


def _apply_memory_link_if_needed(isr: ISR, session: SessionCtx, trace: Trace) -> ISR:
    entries = []
    for node in isr.context:
        if node.kind is not NodeKind.STRUCT:
            continue
        fields = dict(node.fields)
        tag = fields.get("tag")
        if not tag or (tag.label or "").lower() != "memory_entry":
            continue
        entries.append(node)
    if not entries:
        return isr
    for entry in entries:
        isr = apply_operator(isr, operation("MEMORY_LINK", entry), session)
        trace.add("Φ_MEMORY[LINK]", isr.quality, len(isr.relations), len(isr.context))
    return isr


def _format_normalize_trace_label(base_label: str, context: Tuple[Node, ...]) -> str:
    summary = _latest_tagged_struct(context, "normalize_summary")
    if summary is None:
        return base_label
    fields = dict(summary.fields)
    total = _node_numeric(fields.get("total"))
    deduped = _node_numeric(fields.get("deduped"))
    removed = _node_numeric(fields.get("removed"))
    aggressive = _node_numeric(fields.get("aggressive_removed"))
    parts = []
    if total is not None:
        parts.append(f"tot={total}")
    if deduped is not None:
        parts.append(f"dedup={deduped}")
    if removed is not None:
        parts.append(f"rem={removed}")
    if aggressive:
        parts.append(f"agg={aggressive}")
    if not parts:
        return base_label
    return f"{base_label}[{','.join(parts)}]"


def _memory_entry_payload(
    meta_info: MetaTransformResult | None,
    answer_text: str,
    meta_expression: Node | None,
    reasoning_node: Node | None,
    reflection_node: Node | None,
    justification_node: Node | None,
    meta_equation: Node | None,
    logic_proof: Node | None = None,
    meta_synthesis: Node | None = None,
) -> dict[str, object]:
    route = meta_info.route.value if meta_info else ""
    payload = {
        "route": route,
        "answer": answer_text,
        "expression_preview": _node_field_label(meta_expression, "preview"),
        "expression_answer_digest": _node_field_label(meta_expression, "answer_digest"),
        "reasoning_trace_digest": _node_field_label(reasoning_node, "digest"),
        "reflection_digest": _node_field_label(reflection_node, "digest"),
        "reflection_phase_chain": _node_field_label(reflection_node, "phase_chain"),
    }
    justification_digest = _node_field_label(justification_node, "digest")
    justification_depth = _node_field_label(justification_node, "depth")
    justification_width = _node_field_label(justification_node, "width")
    if justification_digest:
        payload["justification_digest"] = justification_digest
    if justification_depth:
        payload["justification_depth"] = justification_depth
    if justification_width:
        payload["justification_width"] = justification_width
    if meta_equation is not None:
        payload["equation_digest"] = _node_field_label(meta_equation, "digest")
        payload["equation_quality"] = _node_field_label(meta_equation, "quality")
        payload["equation_trend"] = _node_field_label(meta_equation, "trend")
        payload["equation_delta_quality"] = _node_field_label(meta_equation, "delta_quality")
    if logic_proof is not None:
        payload["logic_proof_truth"] = _node_field_label(logic_proof, "truth")
        payload["logic_proof_query"] = _node_field_label(logic_proof, "query")
        payload["logic_proof_digest"] = fingerprint(logic_proof)
    if meta_synthesis is not None:
        payload.update(_synthesis_snapshot(meta_synthesis))
    return payload


def _synthesis_snapshot(meta_synthesis: Node) -> dict[str, object]:
    if meta_synthesis.kind is not NodeKind.STRUCT:
        return {}
    fields = dict(meta_synthesis.fields)
    snapshot: dict[str, object] = {}
    plan_total = _node_numeric(fields.get("plan_total"))
    proof_total = _node_numeric(fields.get("proof_total"))
    program_total = _node_numeric(fields.get("program_total"))
    if plan_total:
        snapshot["synthesis_plan_total"] = plan_total
    if proof_total:
        snapshot["synthesis_proof_total"] = proof_total
    if program_total:
        snapshot["synthesis_program_total"] = program_total
    plans_node = fields.get("plans")
    if plans_node is not None:
        snapshot["synthesis_plan_sources"] = _collect_synthesis_sources(plans_node, "source_digest")
    proofs_node = fields.get("proofs")
    if proofs_node is not None:
        snapshot["synthesis_proof_sources"] = _collect_synthesis_sources(proofs_node, "proof_digest")
    programs_node = fields.get("programs")
    if programs_node is not None:
        snapshot["synthesis_program_sources"] = _collect_synthesis_sources(programs_node, "source_digest")
    return snapshot


def _collect_synthesis_sources(node: Node, field_name: str) -> list[str]:
    if node.kind is not NodeKind.LIST:
        return []
    values: list[str] = []
    for entry in node.args:
        if entry.kind is not NodeKind.STRUCT:
            continue
        value_node = dict(entry.fields).get(field_name)
        if value_node and value_node.label:
            values.append(value_node.label)
    return values


def _node_field_label(node: Node | None, field: str) -> str:
    if node is None:
        return ""
    value = dict(node.fields).get(field)
    if value is None:
        return ""
    if value.label:
        return value.label
    if value.value is not None:
        return str(value.value)
    return ""


def _node_numeric(node: Node | None) -> int | None:
    if node is None or node.value is None:
        return None
    try:
        return int(node.value)
    except (TypeError, ValueError):
        return None


def _latest_logic_proof(context: Tuple[Node, ...]) -> Node | None:
    return _latest_tagged_struct(context, "logic_proof")


def _ensure_memory_loaded(session: SessionCtx) -> None:
    if session.memory_loaded:
        return
    session.memory_loaded = True
    path = getattr(session.config, "memory_store_path", None)
    if not path:
        return
    limit = getattr(session.config, "memory_persist_limit", 0) or session.config.meta_history_limit
    nodes = load_recent_memory(path, limit)
    if nodes:
        session.meta_buffer = tuple((*nodes, *session.meta_buffer))


def _persist_meta_memory(session: SessionCtx, memory_node: Node | None) -> None:
    if memory_node is None:
        return
    path = getattr(session.config, "memory_store_path", None)
    if not path:
        return
    try:
        append_memory(path, memory_node)
    except OSError:
        return


def _record_episode(session: SessionCtx, text: str, outcome: RunOutcome) -> None:
    path = getattr(session.config, "episodes_path", None)
    if path:
        try:
            record_episode(path, text, outcome)
        except OSError:
            pass
    _maybe_run_memory_induction(session)


def _maybe_run_memory_induction(session: SessionCtx) -> None:
    episodes_path = getattr(session.config, "episodes_path", None)
    suggestions_path = getattr(session.config, "induction_rules_path", None)
    limit = getattr(session.config, "induction_episode_limit", 0)
    support = getattr(session.config, "induction_min_support", 0)
    if not episodes_path or not suggestions_path or limit <= 0:
        return
    try:
        run_memory_induction(
            episodes_path,
            suggestions_path,
            episode_limit=limit,
            min_support=max(1, support),
        )
    except OSError:
        return


def _finalize_outcome(session: SessionCtx, text: str, outcome: RunOutcome) -> RunOutcome:
    _record_episode(session, text, outcome)
    return outcome


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
    logic_proof_node: Node | None = None
    if (meta.trace_label or "").startswith("LOGIC[QUERY"):
        isr = apply_operator(isr, operation("PROVE", meta.struct_node), session)
        logic_proof_node = _latest_logic_proof(isr.context)
    answer_text = _answer_text(isr)
    reasoning_node = build_meta_reasoning(trace.steps)
    reflection_node = build_meta_reflection(reasoning_node)
    justification_node = build_meta_justification(reasoning_node)
    isr = _apply_trace_summary_if_needed(isr, session, reasoning_node, trace)
    isr = _apply_reflection_summary_if_needed(isr, session, reflection_node, trace)
    language = _resolve_language(meta, session)
    memory_refs = tuple(node for node in session.meta_buffer if node is not None)
    meta_expression = build_meta_expression(
        isr.answer,
        reasoning=reasoning_node,
        reflection=reflection_node,
        quality=isr.quality,
        halt_reason=HaltReason.PLAN_EXECUTED.value,
        route=meta.route,
        language=language,
        memory_refs=memory_refs,
    )
    equation_node = build_meta_equation_node(snapshot, session.last_equation_stats)
    equation_stats = snapshot.stats()
    memory_entry = _memory_entry_payload(
        meta,
        answer_text,
        meta_expression,
        reasoning_node,
        reflection_node,
        justification_node,
        equation_node,
        logic_proof_node,
    )
    meta_memory = build_meta_memory(session.meta_history, memory_entry)
    meta_summary = build_meta_summary(
        meta,
        answer_text,
        isr.quality,
        HaltReason.PLAN_EXECUTED.value,
        calc_result,
        meta_reasoning=reasoning_node,
        meta_reflection=reflection_node,
        meta_justification=justification_node,
        meta_expression=meta_expression,
        meta_memory=meta_memory,
        meta_equation=equation_node,
        meta_proof=logic_proof_node,
    )
    session.meta_history.append(meta_summary)
    limit = getattr(session.config, "meta_history_limit", 0)
    if limit and len(session.meta_history) > limit:
        del session.meta_history[:-limit]
    session.meta_buffer = (
        tuple(meta_ctx for meta_ctx in session.meta_buffer if meta_ctx is not None) + ((meta_memory,) if meta_memory else tuple())
    )
    _persist_meta_memory(session, meta_memory)
    session.last_equation_stats = equation_stats
    outcome = RunOutcome(
        answer=answer_text,
        trace=trace,
        isr=isr,
        halt_reason=HaltReason.PLAN_EXECUTED,
        finalized=True,
        equation=snapshot,
        equation_digest=snapshot.digest(),
        explanation=render_explanation(isr, meta.struct_node),
        meta_summary=meta_summary,
        meta_reasoning=reasoning_node,
        meta_reflection=reflection_node,
        meta_justification=justification_node,
        meta_expression=meta_expression,
        meta_memory=meta_memory,
        calc_plan=plan,
        calc_result=calc_result,
        lc_meta=meta.lc_meta,
        language_profile=meta.language_profile,
        code_ast=meta.code_ast,
        code_summary=meta.code_summary,
        math_ast=meta.math_ast,
    )
    return outcome


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
