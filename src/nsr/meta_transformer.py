"""
Meta-Transformador: converte entradas cruas em meta-representações LIU auditáveis.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from hashlib import blake2b
from typing import Tuple, TYPE_CHECKING, Any
import json

from liu import (
    Node,
    struct as liu_struct,
    entity,
    text as liu_text,
    number,
    to_json,
    list_node,
    fingerprint,
    from_json,
)

if TYPE_CHECKING:
    from .meta_calculator import MetaCalculationResult

from .code_bridge import maybe_route_code
from .ian_bridge import maybe_route_text
from .lex import DEFAULT_LEXICON, tokenize
from .logic_bridge import maybe_route_logic
from .math_bridge import maybe_route_math
from .polynomial_bridge import maybe_route_polynomial
from .bayes_bridge import maybe_route_bayes
from .markov_bridge import maybe_route_markov
from .regression_bridge import maybe_route_regression
from .factor_bridge import maybe_route_factor
from .parser import build_struct
from .state import SessionCtx
from .meta_structures import maybe_build_lc_meta_struct, meta_calculation_to_node
from .language_detector import detect_language_profile, language_profile_to_node
from .code_ast import build_python_ast_meta, build_code_ast_summary
from .lc_omega import MetaCalculation, LCTerm
from .meta_calculus_router import text_opcode_pipeline, text_operation_pipeline, detect_plan_goal
from svm.vm import Program
from svm.bytecode import Instruction
from svm.opcodes import Opcode


class MetaRoute(str, Enum):
    """Classifica o caminho determinístico usado para gerar a meta-representação."""

    MATH = "math"
    LOGIC = "logic"
    CODE = "code"
    INSTINCT = "instinct"
    TEXT = "text"
    STAT = "stat"


@dataclass(frozen=True, slots=True)
class MetaTransformResult:
    """Resultado imutável do estágio Meta-LER."""

    struct_node: Node
    route: MetaRoute
    input_text: str
    trace_label: str | None = None
    preseed_answer: Node | None = None
    preseed_context: Tuple[Node, ...] | None = None
    preseed_quality: float | None = None
    language_hint: str | None = None
    calc_plan: "MetaCalculationPlan | None" = None
    lc_meta: Node | None = None
    meta_calculation: MetaCalculation | None = None
    phi_plan_ops: Tuple[str, ...] | None = None
    language_profile: Node | None = None
    code_ast: Node | None = None
    code_summary: Node | None = None
    math_ast: Node | None = None
    plan_goal: str | None = None


@dataclass(frozen=True, slots=True)
class MetaCalculationPlan:
    """Plano determinístico de meta-cálculo pronto para ΣVM."""

    route: MetaRoute
    program: Program
    description: str


class MetaTransformer:
    """
    Responsável por aplicar o estágio Meta-LER do pipeline.

    Ele tenta roteamentos determinísticos na ordem:
    matemática → lógica → instinto linguístico → parser textual.
    """

    __slots__ = ("session",)

    def __init__(self, session: SessionCtx) -> None:
        self.session = session

    def transform(self, text_value: str) -> MetaTransformResult:
        """Executa o pipeline de roteamento determinístico."""

        detection = detect_language_profile(text_value)
        language_profile_node = language_profile_to_node(detection)
        language_hint = (self.session.language_hint or "").lower() or None
        if detection.category == "text" and detection.language:
            language_hint = detection.language.lower()
            self.session.language_hint = language_hint
        should_build_code_ast = detection.category == "code" and detection.dialect == "python"

        poly_hook = None
        math_hook = None
        if detection.category != "code":
            poly_hook = maybe_route_polynomial(text_value)
            if poly_hook is None:
                math_hook = maybe_route_math(text_value)
        if poly_hook:
            plan = _direct_answer_plan(MetaRoute.MATH, poly_hook.answer_node)
            preseed_context = self._with_meta_context(
                poly_hook.context_nodes,
                MetaRoute.MATH,
                self.session.language_hint,
                text_value,
                language_profile_node,
            )
            plan_node = _meta_plan_node(MetaRoute.MATH, None, plan)
            if plan_node is not None:
                preseed_context = tuple((*preseed_context, plan_node))
            return MetaTransformResult(
                struct_node=poly_hook.struct_node,
                route=MetaRoute.MATH,
                input_text=text_value,
                trace_label=poly_hook.trace_label,
                preseed_answer=poly_hook.answer_node,
                preseed_context=preseed_context,
                preseed_quality=poly_hook.quality,
                language_hint=self.session.language_hint,
                calc_plan=plan,
                language_profile=language_profile_node,
                code_ast=None,
                math_ast=None,
            )

        if math_hook:
            plan = _direct_answer_plan(MetaRoute.MATH, math_hook.answer_node)
            self.session.language_hint = math_hook.reply.language
            preseed_context = self._with_meta_context(
                math_hook.context_nodes,
                MetaRoute.MATH,
                math_hook.reply.language,
                text_value,
                language_profile_node,
            )
            plan_node = _meta_plan_node(MetaRoute.MATH, None, plan)
            if plan_node is not None:
                preseed_context = tuple((*preseed_context, plan_node))
            return MetaTransformResult(
                struct_node=math_hook.struct_node,
                route=MetaRoute.MATH,
                input_text=text_value,
                trace_label=f"MATH[{math_hook.utterance.role}]",
                preseed_answer=math_hook.answer_node,
                preseed_context=preseed_context,
                preseed_quality=math_hook.quality,
                language_hint=math_hook.reply.language,
                calc_plan=plan,
                language_profile=language_profile_node,
                code_ast=None,
                math_ast=math_hook.math_ast,
            )

        logic_hook = maybe_route_logic(text_value, engine=self.session.logic_engine)
        if logic_hook:
            plan = _direct_answer_plan(MetaRoute.LOGIC, logic_hook.answer_node)
            self.session.logic_engine = logic_hook.result.engine
            self.session.logic_serialized = logic_hook.snapshot
            preseed_context = self._with_meta_context(
                logic_hook.context_nodes,
                MetaRoute.LOGIC,
                self.session.language_hint,
                text_value,
                language_profile_node,
            )
            plan_node = _meta_plan_node(MetaRoute.LOGIC, None, plan)
            if plan_node is not None:
                preseed_context = tuple((*preseed_context, plan_node))
            return MetaTransformResult(
                struct_node=logic_hook.struct_node,
                route=MetaRoute.LOGIC,
                input_text=text_value,
                trace_label=logic_hook.trace_label,
                preseed_answer=logic_hook.answer_node,
                preseed_context=preseed_context,
                preseed_quality=logic_hook.quality,
                calc_plan=plan,
                language_profile=language_profile_node,
                code_ast=None,
                math_ast=None,
            )

        bayes_hook = maybe_route_bayes(text_value)
        if bayes_hook:
            plan = _direct_answer_plan(MetaRoute.STAT, bayes_hook.answer_node)
            preseed_context = self._with_meta_context(
                bayes_hook.context_nodes,
                MetaRoute.STAT,
                self.session.language_hint,
                text_value,
                language_profile_node,
            )
            plan_node = _meta_plan_node(MetaRoute.STAT, None, plan)
            if plan_node is not None:
                preseed_context = tuple((*preseed_context, plan_node))
            return MetaTransformResult(
                struct_node=bayes_hook.struct_node,
                route=MetaRoute.STAT,
                input_text=text_value,
                trace_label=bayes_hook.trace_label,
                preseed_answer=bayes_hook.answer_node,
                preseed_context=preseed_context,
                preseed_quality=bayes_hook.quality,
                calc_plan=plan,
                language_profile=language_profile_node,
                code_ast=None,
                math_ast=None,
            )

        markov_hook = maybe_route_markov(text_value)
        if markov_hook:
            plan = _direct_answer_plan(MetaRoute.STAT, markov_hook.answer_node)
            preseed_context = self._with_meta_context(
                markov_hook.context_nodes,
                MetaRoute.STAT,
                self.session.language_hint,
                text_value,
                language_profile_node,
            )
            plan_node = _meta_plan_node(MetaRoute.STAT, None, plan)
            if plan_node is not None:
                preseed_context = tuple((*preseed_context, plan_node))
            return MetaTransformResult(
                struct_node=markov_hook.struct_node,
                route=MetaRoute.STAT,
                input_text=text_value,
                trace_label=markov_hook.trace_label,
                preseed_answer=markov_hook.answer_node,
                preseed_context=preseed_context,
                preseed_quality=markov_hook.quality,
                calc_plan=plan,
                language_profile=language_profile_node,
                code_ast=None,
                math_ast=None,
            )

        regression_hook = maybe_route_regression(text_value)
        if regression_hook:
            plan = _direct_answer_plan(MetaRoute.STAT, regression_hook.answer_node)
            preseed_context = self._with_meta_context(
                regression_hook.context_nodes,
                MetaRoute.STAT,
                self.session.language_hint,
                text_value,
                language_profile_node,
            )
            plan_node = _meta_plan_node(MetaRoute.STAT, None, plan)
            if plan_node is not None:
                preseed_context = tuple((*preseed_context, plan_node))
            return MetaTransformResult(
                struct_node=regression_hook.struct_node,
                route=MetaRoute.STAT,
                input_text=text_value,
                trace_label=regression_hook.trace_label,
                preseed_answer=regression_hook.answer_node,
                preseed_context=preseed_context,
                preseed_quality=regression_hook.quality,
                calc_plan=plan,
                language_profile=language_profile_node,
                code_ast=None,
                math_ast=None,
            )

        factor_hook = maybe_route_factor(text_value)
        if factor_hook:
            plan = _direct_answer_plan(MetaRoute.STAT, factor_hook.answer_node)
            preseed_context = self._with_meta_context(
                factor_hook.context_nodes,
                MetaRoute.STAT,
                self.session.language_hint,
                text_value,
                language_profile_node,
            )
            plan_node = _meta_plan_node(MetaRoute.STAT, None, plan)
            if plan_node is not None:
                preseed_context = tuple((*preseed_context, plan_node))
            return MetaTransformResult(
                struct_node=factor_hook.struct_node,
                route=MetaRoute.STAT,
                input_text=text_value,
                trace_label=factor_hook.trace_label,
                preseed_answer=factor_hook.answer_node,
                preseed_context=preseed_context,
                preseed_quality=factor_hook.quality,
                calc_plan=plan,
                language_profile=language_profile_node,
                code_ast=None,
                math_ast=None,
            )

        code_hook = maybe_route_code(
            text_value,
            dialect=detection.dialect if detection.category == "code" else None,
        )
        if code_hook:
            plan = _direct_answer_plan(MetaRoute.CODE, code_hook.answer_node)
            preseed_context = self._with_meta_context(
                code_hook.context_nodes,
                MetaRoute.CODE,
                code_hook.language,
                text_value,
                language_profile_node,
            )
            summary_node = build_code_ast_summary(code_hook.ast_node) if code_hook.ast_node is not None else None
            if summary_node is not None:
                preseed_context = tuple((*preseed_context, summary_node))
            plan_node = _meta_plan_node(MetaRoute.CODE, None, plan)
            if plan_node is not None:
                preseed_context = tuple((*preseed_context, plan_node))
            return MetaTransformResult(
                struct_node=code_hook.struct_node,
                route=MetaRoute.CODE,
                input_text=text_value,
                trace_label=code_hook.trace_label,
                preseed_answer=code_hook.answer_node,
                preseed_context=preseed_context,
                preseed_quality=code_hook.quality,
                language_hint=code_hook.language,
                calc_plan=plan,
                language_profile=language_profile_node,
                code_ast=code_hook.ast_node,
                code_summary=summary_node,
                math_ast=None,
            )

        instinct_hook = maybe_route_text(text_value)
        if instinct_hook:
            plan = _direct_answer_plan(MetaRoute.INSTINCT, instinct_hook.answer_node)
            self.session.language_hint = instinct_hook.reply_plan.language
            preseed_context = self._with_meta_context(
                instinct_hook.context_nodes,
                MetaRoute.INSTINCT,
                instinct_hook.reply_plan.language,
                text_value,
                language_profile_node,
            )
            plan_node = _meta_plan_node(MetaRoute.INSTINCT, None, plan)
            if plan_node is not None:
                preseed_context = tuple((*preseed_context, plan_node))
            return MetaTransformResult(
                struct_node=instinct_hook.struct_node,
                route=MetaRoute.INSTINCT,
                input_text=text_value,
                trace_label=f"IAN[{instinct_hook.utterance.role}]",
                preseed_answer=instinct_hook.answer_node,
                preseed_context=preseed_context,
                preseed_quality=instinct_hook.quality,
                language_hint=instinct_hook.reply_plan.language,
                calc_plan=plan,
                language_profile=language_profile_node,
                code_ast=None,
                math_ast=None,
            )

        language = (language_hint or "pt").lower()
        lexicon = self._effective_lexicon()
        tokens = tokenize(text_value, lexicon)
        struct_node = build_struct(tokens, language=language, text_input=text_value)
        struct_node = attach_language_field(struct_node, language)
        lc_meta_node, lc_parsed = maybe_build_lc_meta_struct(language, text_value)
        effective_calculus = lc_parsed.calculus if lc_parsed else None
        if lc_parsed:
            effective_calculus = _maybe_state_followup(
                effective_calculus, lc_parsed.term, bool(self.session.meta_buffer)
            )
        if lc_meta_node is not None and effective_calculus is not None:
            lc_meta_node = _set_struct_field(
                lc_meta_node, "calculus", meta_calculation_to_node(effective_calculus)
            )
        if lc_meta_node is not None:
            struct_node = _set_struct_field(struct_node, "lc_meta", lc_meta_node, overwrite=False)
        text_plan = _text_phi_plan(calculus=effective_calculus)
        meta_context = self._with_meta_context(
            None,
            MetaRoute.TEXT,
            language,
            text_value,
            language_profile_node,
        )
        if lc_meta_node is not None:
            meta_context = tuple((*meta_context, lc_meta_node))
        phi_plan_ops: Tuple[str, ...] | None = None
        if lc_parsed and lc_parsed.calculus:
            ops = text_operation_pipeline(lc_parsed.calculus, None)
            filtered = tuple((op.label or "") for op in ops if (op.label or ""))
            if filtered:
                phi_plan_ops = filtered
        plan_goal_text = detect_plan_goal(effective_calculus, text_value)
        if plan_goal_text:
            if phi_plan_ops:
                phi_plan_ops = ("PLAN_DECOMPOSE", *phi_plan_ops)
            else:
                phi_plan_ops = ("PLAN_DECOMPOSE",)
        fallback_code_ast = None
        code_summary = None
        if should_build_code_ast:
            fallback_code_ast = build_python_ast_meta(text_value)
            if fallback_code_ast is not None:
                meta_context = tuple((*meta_context, fallback_code_ast))
                code_summary = build_code_ast_summary(fallback_code_ast)
                meta_context = tuple((*meta_context, code_summary))
        plan_context = _meta_plan_node(MetaRoute.TEXT, phi_plan_ops, text_plan)
        if plan_context is not None:
            meta_context = tuple((*meta_context, plan_context))
        return MetaTransformResult(
            struct_node=struct_node,
            route=MetaRoute.TEXT,
            input_text=text_value,
            preseed_context=meta_context,
            language_hint=language,
            calc_plan=text_plan,
            lc_meta=lc_meta_node,
            meta_calculation=effective_calculus,
            phi_plan_ops=phi_plan_ops,
            language_profile=language_profile_node,
            code_ast=fallback_code_ast,
            code_summary=code_summary,
            math_ast=None,
            plan_goal=plan_goal_text,
        )

    def _effective_lexicon(self):
        lexicon = self.session.lexicon
        if lexicon.synonyms or lexicon.pos_hint or lexicon.qualifiers or lexicon.rel_words:
            return lexicon
        return DEFAULT_LEXICON

    def _with_meta_context(
        self,
        base_context: Tuple[Node, ...] | None,
        route: MetaRoute,
        language: str | None,
        text_value: str,
        language_profile: Node | None,
    ) -> Tuple[Node, ...]:
        route_node = _meta_route_node(route, language)
        input_node = _meta_input_node(text_value)
        extra: Tuple[Node, ...]
        if language_profile is not None:
            extra = (route_node, input_node, language_profile)
        else:
            extra = (route_node, input_node)
        if base_context:
            return tuple((*base_context, *extra))
        return extra


def attach_language_field(node: Node, language: str | None) -> Node:
    """Garante que a estrutura LIU carregue o campo `language`."""

    if not language:
        return node
    return _set_struct_field(node, "language", entity(language), overwrite=False)


def _set_struct_field(node: Node, key: str, value: Node, *, overwrite: bool = True) -> Node:
    fields = dict(node.fields)
    if not overwrite and key in fields:
        return node
    fields[key] = value
    return liu_struct(**fields)


__all__ = [
    "MetaTransformer",
    "MetaTransformResult",
    "MetaRoute",
    "attach_language_field",
    "build_meta_summary",
    "meta_summary_to_dict",
    "MetaCalculationPlan",
]


def _meta_route_node(route: MetaRoute, language: str | None) -> Node:
    fields: dict[str, Node] = {
        "tag": entity("meta_route"),
        "route": entity(route.value),
    }
    if language:
        fields["language"] = entity(language)
    return liu_struct(**fields)


def _meta_input_node(text_value: str) -> Node:
    preview = text_value if len(text_value) <= 120 else text_value[:117] + "..."
    return liu_struct(
        tag=entity("meta_input"),
        size=number(len(text_value)),
        preview=liu_text(preview),
    )


def _meta_output_node(answer_text: str, quality: float, halt_reason: str) -> Node:
    return liu_struct(
        tag=entity("meta_output"),
        answer=liu_text(answer_text),
        quality=number(round(quality, 4)),
        halt=entity(halt_reason.lower()),
    )


def _meta_calc_node(calc_node: Node) -> Node:
    return liu_struct(
        tag=entity("meta_calc"),
        payload=calc_node,
    )


def _meta_plan_node(
    route: MetaRoute,
    plan_ops: Tuple[str, ...] | None,
    plan: MetaCalculationPlan | None = None,
) -> Node | None:
    include_ops = bool(plan_ops)
    include_plan = plan is not None
    if not include_ops and not include_plan:
        return None
    fields: dict[str, Node] = {
        "tag": entity("meta_plan"),
        "route": entity(route.value),
    }
    if plan_ops:
        ops_nodes = [entity(label) for label in plan_ops if label]
        if ops_nodes:
            chain = "→".join(plan_ops)
            fields["chain"] = liu_text(chain)
            fields["ops"] = list_node(ops_nodes)
    if plan is not None:
        fields["description"] = entity(plan.description)
        fields["program_len"] = number(len(plan.program.instructions))
        fields["const_len"] = number(len(plan.program.constants))
        fields["digest"] = entity(_plan_digest(plan))
    if len(fields) == 2:
        return None
    return liu_struct(**fields)


def _plan_digest(plan: MetaCalculationPlan) -> str:
    hasher = blake2b(digest_size=16)
    hasher.update(plan.route.value.encode("utf-8"))
    hasher.update(plan.description.encode("utf-8"))
    for inst in plan.program.instructions:
        hasher.update(f"{inst.opcode.name}:{inst.operand}".encode("utf-8"))
    hasher.update(b"|")
    for constant in plan.program.constants:
        hasher.update(_constant_signature(constant).encode("utf-8"))
    return hasher.hexdigest()


def _constant_signature(value: object) -> str:
    if isinstance(value, Node):
        return fingerprint(value)
    if value is None:
        return "NULL"
    if isinstance(value, (int, float, bool)):
        return str(value)
    return repr(value)


def build_meta_summary(
    meta: MetaTransformResult,
    answer_text: str,
    quality: float,
    halt_reason: str,
    calc_result: "MetaCalculationResult | None" = None,
    meta_reasoning: Node | None = None,
    meta_reflection: Node | None = None,
    meta_justification: Node | None = None,
    meta_expression: Node | None = None,
    meta_memory: Node | None = None,
    meta_equation: Node | None = None,
    meta_proof: Node | None = None,
    meta_context_prob: Node | None = None,
    meta_synthesis: Node | None = None,
) -> Tuple[Node, ...]:
    nodes = [
        _meta_route_node(meta.route, meta.language_hint),
        _meta_input_node(meta.input_text),
        _meta_output_node(answer_text, quality, halt_reason),
    ]
    calc_node = _extract_meta_calculation(meta)
    if calc_node is not None:
        nodes.append(calc_node)
    plan_node = _meta_plan_node(meta.route, meta.phi_plan_ops, meta.calc_plan)
    if plan_node is not None:
        nodes.append(plan_node)
    if meta.language_profile is not None:
        nodes.append(meta.language_profile)
    if meta.code_ast is not None:
        nodes.append(meta.code_ast)
    if meta.code_summary is not None:
        nodes.append(meta.code_summary)
    if meta.math_ast is not None:
        nodes.append(meta.math_ast)
    if calc_result is not None:
        exec_node = _meta_calc_exec_node(calc_result)
        if exec_node is not None:
            nodes.append(exec_node)
    if meta_reasoning is not None:
        nodes.append(meta_reasoning)
    if meta_reflection is not None:
        nodes.append(meta_reflection)
    if meta_justification is not None:
        nodes.append(meta_justification)
    if meta_expression is not None:
        nodes.append(meta_expression)
    if meta_memory is not None:
        nodes.append(meta_memory)
    if meta_synthesis is not None:
        nodes.append(meta_synthesis)
    if meta_context_prob is not None:
        nodes.append(meta_context_prob)
    if meta_equation is not None:
        nodes.append(meta_equation)
    if meta_proof is not None:
        nodes.append(_meta_proof_node(meta_proof))
    nodes.append(_meta_digest_node(nodes))
    return tuple(nodes)


def meta_summary_to_dict(summary: Tuple[Node, ...]) -> dict[str, object]:
    nodes = {dict(node.fields)["tag"].label: node for node in summary}
    route_fields = _fields(nodes["meta_route"])
    input_fields = _fields(nodes["meta_input"])
    output_fields = _fields(nodes["meta_output"])
    result = {
        "route": _label(route_fields["route"]),
        "language": _label(route_fields.get("language")),
        "input_size": _value(input_fields["size"]),
        "input_preview": _label(input_fields["preview"]),
        "answer": _label(output_fields["answer"]),
        "quality": _value(output_fields["quality"]),
        "halt": _label(output_fields["halt"]),
    }
    calc_node = nodes.get("meta_calc")
    if calc_node is not None:
        calc_fields = _fields(calc_node)
        payload = calc_fields.get("payload")
        if payload is not None:
            result["meta_calculation"] = to_json(payload)
    plan_node = nodes.get("meta_plan")
    if plan_node is not None:
        plan_fields = _fields(plan_node)
        result["phi_plan_route"] = _label(plan_fields.get("route"))
        result["phi_plan_chain"] = _label(plan_fields.get("chain"))
        result["phi_plan_description"] = _label(plan_fields.get("description"))
        result["phi_plan_digest"] = _label(plan_fields.get("digest"))
        prog_len = plan_fields.get("program_len")
        if prog_len is not None:
            result["phi_plan_program_len"] = int(_value(prog_len))
        const_len = plan_fields.get("const_len")
        if const_len is not None:
            result["phi_plan_const_len"] = int(_value(const_len))
        ops_node = plan_fields.get("ops")
        if ops_node is not None and ops_node.kind.name == "LIST":
            result["phi_plan_ops"] = [(arg.label or "") for arg in ops_node.args]
    profile_node = nodes.get("language_profile")
    if profile_node is not None:
        profile_fields = _fields(profile_node)
        result["language_category"] = _label(profile_fields.get("category"))
        result["language_detected"] = _label(profile_fields.get("language"))
        result["language_dialect"] = _label(profile_fields.get("dialect"))
        result["language_confidence"] = _value(profile_fields.get("confidence"))
        hints_node = profile_fields.get("hints")
        if hints_node is not None and hints_node.kind.name == "LIST":
            result["language_hints"] = [(arg.label or "") for arg in hints_node.args]
    code_ast_node = nodes.get("code_ast")
    if code_ast_node is not None:
        ast_fields = _fields(code_ast_node)
        result["code_ast_language"] = _label(ast_fields.get("language"))
        count_node = ast_fields.get("node_count")
        if count_node is not None:
            result["code_ast_node_count"] = int(_value(count_node))
        truncated_node = ast_fields.get("truncated")
        if truncated_node is not None:
            result["code_ast_truncated"] = (_label(truncated_node).lower() == "true")
    code_summary_node = nodes.get("code_ast_summary")
    if code_summary_node is not None:
        summary_fields = _fields(code_summary_node)
        result["code_summary_language"] = _label(summary_fields.get("language"))
        node_count = summary_fields.get("node_count")
        if node_count is not None:
            result["code_summary_node_count"] = int(_value(node_count))
        fn_count = summary_fields.get("function_count")
        if fn_count is not None:
            result["code_summary_function_count"] = int(_value(fn_count))
        result["code_summary_digest"] = _label(summary_fields.get("digest"))
        functions_node = summary_fields.get("functions")
        if functions_node is not None and functions_node.kind.name == "LIST":
            function_names: list[str] = []
            function_details: list[dict[str, object]] = []
            for entry in functions_node.args:
                entry_fields = _fields(entry)
                name = _label(entry_fields.get("name"))
                if name:
                    function_names.append(name)
                detail: dict[str, object] = {"name": name}
                param_count_node = entry_fields.get("param_count")
                if param_count_node is not None:
                    detail["param_count"] = int(_value(param_count_node))
                params_node = entry_fields.get("parameters")
                if params_node is not None and params_node.kind.name == "LIST":
                    detail["parameters"] = [_label(arg) for arg in params_node.args]
                function_details.append(detail)
            if function_names:
                result["code_summary_functions"] = function_names
            if any(item.get("name") for item in function_details):
                result["code_summary_function_details"] = function_details
    math_ast_node = nodes.get("math_ast")
    if math_ast_node is not None:
          math_fields = _fields(math_ast_node)
          result["math_ast_operator"] = _label(math_fields.get("operator"))
          result["math_ast_language"] = _label(math_fields.get("language"))
          result["math_ast_expression"] = _label(math_fields.get("expression"))
          operand_node = math_fields.get("operand_count")
          if operand_node is not None:
              result["math_ast_operand_count"] = int(_value(operand_node))
          value_node = math_fields.get("value")
          if value_node is not None:
              result["math_ast_value"] = _value(value_node)
    reasoning_node = nodes.get("meta_reasoning")
    if reasoning_node is not None:
          reasoning_fields = _fields(reasoning_node)
          step_count_node = reasoning_fields.get("step_count")
          if step_count_node is not None:
              result["reasoning_step_count"] = int(_value(step_count_node))
          digest_value = reasoning_fields.get("digest")
          if digest_value is not None:
              result["reasoning_trace_digest"] = _label(digest_value)
          operations_node = reasoning_fields.get("operations")
          if operations_node is not None and operations_node.kind.name == "LIST":
              ops_labels: list[str] = []
              op_details: list[dict[str, object]] = []
              for entry in operations_node.args:
                  entry_fields = _fields(entry)
                  label = _label(entry_fields.get("label"))
                  if label:
                      ops_labels.append(label)
                  index_node = entry_fields.get("index")
                  if index_node is None:
                      continue  # Skip malformed entries
                  detail: dict[str, object] = {
                      "index": int(_value(index_node)),
                      "label": label,
                  }
                  quality_node = entry_fields.get("quality")
                  if quality_node is not None:
                      detail["quality"] = _value(quality_node)
                  relations_node = entry_fields.get("relations")
                  if relations_node is not None:
                      detail["relations"] = int(_value(relations_node))
                  context_node = entry_fields.get("context")
                  if context_node is not None:
                      detail["context"] = int(_value(context_node))
                  op_details.append(detail)
              if ops_labels:
                  result["reasoning_ops"] = ops_labels
              if op_details:
                  result["reasoning_steps"] = op_details
          stats_node = reasoning_fields.get("operator_stats")
          if stats_node is not None and stats_node.kind.name == "LIST":
              stats_list: list[dict[str, object]] = []
              for entry in stats_node.args:
                  entry_fields = _fields(entry)
                  stats_list.append(
                      {
                          "label": _label(entry_fields.get("label")),
                          "count": int(_value(entry_fields.get("count"))),
                      }
                  )
              if stats_list:
                  result["reasoning_operator_stats"] = stats_list
    reflection_node = nodes.get("meta_reflection")
    if reflection_node is not None:
        reflection_fields = _fields(reflection_node)
        phase_count_node = reflection_fields.get("phase_count")
        decision_count_node = reflection_fields.get("decision_count")
        result["reflection_phase_count"] = int(_value(phase_count_node)) if phase_count_node else 0
        result["reflection_decision_count"] = (
            int(_value(decision_count_node)) if decision_count_node else 0
        )
        result["reflection_phase_chain"] = _label(reflection_fields.get("phase_chain"))
        result["reflection_dominant_phase"] = _label(reflection_fields.get("dominant_phase"))
        result["reflection_digest"] = _label(reflection_fields.get("digest"))
        alert_node = reflection_fields.get("alert_phases")
        if alert_node is not None and alert_node.kind.name == "LIST":
            result["reflection_alert_phases"] = [
                _label(entry) for entry in alert_node.args if _label(entry)
            ]
    justification_node = nodes.get("meta_justification")
    if justification_node is not None:
        justification_fields = _fields(justification_node)
        result["justification_digest"] = _label(justification_fields.get("digest"))
        depth_node = justification_fields.get("depth")
        width_node = justification_fields.get("width")
        count_node = justification_fields.get("node_count")
        if depth_node is not None:
            result["justification_depth"] = int(_value(depth_node))
        if width_node is not None:
            result["justification_width"] = int(_value(width_node))
        if count_node is not None:
            result["justification_node_count"] = int(_value(count_node))
        alert_node = justification_fields.get("alert_phases")
        if alert_node is not None and alert_node.kind.name == "LIST":
            result["justification_alert_phases"] = [
                _label(entry) for entry in alert_node.args if _label(entry)
            ]
        root_node = justification_fields.get("root")
        if root_node is not None:
            root_fields = _fields(root_node)
            result["justification_root_label"] = _label(root_fields.get("label"))
            impact_node = root_fields.get("impact")
            if impact_node is not None:
                impact_fields = _fields(impact_node)
                result["justification_delta_quality"] = _value(impact_fields.get("delta_quality"))
                result["justification_delta_relations"] = _value(impact_fields.get("delta_relations"))
            phases_node = root_fields.get("children")
            if phases_node is not None and phases_node.kind.name == "LIST":
                phases: list[dict[str, object]] = []
                for phase_entry in phases_node.args:
                    phase_fields = _fields(phase_entry)
                    phase_payload: dict[str, object] = {
                        "name": _label(phase_fields.get("name")),
                        "label": _label(phase_fields.get("label")),
                        "step_count": int(_value(phase_fields.get("step_count") or number(0))),
                    }
                    impact = phase_fields.get("impact")
                    if impact is not None:
                        impact_fields = _fields(impact)
                        if impact_fields.get("delta_quality") is not None:
                            phase_payload["delta_quality"] = _value(impact_fields.get("delta_quality"))
                        if impact_fields.get("delta_relations") is not None:
                            phase_payload["delta_relations"] = _value(
                                impact_fields.get("delta_relations")
                            )
                    if phase_fields.get("alert") is not None:
                        phase_payload["alert"] = True
                    phases.append(phase_payload)
                if phases:
                    result["justification_phases"] = phases
    expression_node = nodes.get("meta_expression")
    if expression_node is not None:
        expression_fields = _fields(expression_node)
        result["expression_preview"] = _label(expression_fields.get("preview"))
        result["expression_quality"] = _value(expression_fields.get("quality"))
        result["expression_halt"] = _label(expression_fields.get("halt"))
        result["expression_route"] = _label(expression_fields.get("route"))
        result["expression_language"] = _label(expression_fields.get("language"))
        result["expression_answer_digest"] = _label(expression_fields.get("answer_digest"))
        reasoning_digest = expression_fields.get("reasoning_digest")
        if reasoning_digest is not None:
            result["expression_reasoning_digest"] = _label(reasoning_digest)
        memory_context_node = expression_fields.get("memory_context")
        if memory_context_node is not None and memory_context_node.kind.name == "LIST":
            refs: list[dict[str, object]] = []
            for entry in memory_context_node.args:
                entry_fields = _fields(entry)
                refs.append(
                    {
                        "route": _label(entry_fields.get("route")),
                        "preview": _label(entry_fields.get("preview")),
                        "reasoning_digest": _label(entry_fields.get("reasoning")),
                        "expression_digest": _label(entry_fields.get("expression")),
                    }
                )
            if refs:
                result["expression_memory_context"] = refs
    memory_node = nodes.get("meta_memory")
    if memory_node is not None:
        memory_fields = _fields(memory_node)
        result["memory_size"] = int(_value(memory_fields.get("size")))
        result["memory_digest"] = _label(memory_fields.get("digest"))
        entries_node = memory_fields.get("entries")
        if entries_node is not None and entries_node.kind.name == "LIST":
            memory_entries: list[dict[str, object]] = []
            for entry in entries_node.args:
                entry_fields = _fields(entry)
                memory_entries.append(
                    {
                        "route": _label(entry_fields.get("route")),
                        "answer_preview": _label(entry_fields.get("answer_preview")),
                        "reasoning_digest": _label(entry_fields.get("reasoning_digest")),
                        "expression_digest": _label(entry_fields.get("expression_digest")),
                    }
                )
            result["memory_entries"] = memory_entries
    equation_node = nodes.get("meta_equation")
    if equation_node is not None:
        equation_fields = _fields(equation_node)
        result["equation_digest"] = _label(equation_fields.get("digest"))
        result["equation_input_digest"] = _label(equation_fields.get("input_digest"))
        result["equation_answer_digest"] = _label(equation_fields.get("answer_digest"))
        result["equation_quality"] = _value(equation_fields.get("quality"))
        result["equation_trend"] = _label(equation_fields.get("trend"))
        sections_node = equation_fields.get("sections")
        if sections_node is not None and sections_node.kind.name == "LIST":
            eq_sections: list[dict[str, object]] = []
            for entry in sections_node.args:
                entry_fields = _fields(entry)
                eq_sections.append(
                    {
                        "name": _label(entry_fields.get("name")),
                        "count": int(_value(entry_fields.get("count"))),
                        "digest": _label(entry_fields.get("digest")),
                    }
                )
            result["equation_sections"] = eq_sections
        delta_quality_node = equation_fields.get("delta_quality")
        if delta_quality_node is not None:
            result["equation_delta_quality"] = _value(delta_quality_node)
        delta_sections_node = equation_fields.get("delta_sections")
        if delta_sections_node is not None and delta_sections_node.kind.name == "LIST":
            delta_sections: list[dict[str, object]] = []
            for entry in delta_sections_node.args:
                entry_fields = _fields(entry)
                delta_sections.append(
                    {
                        "name": _label(entry_fields.get("name")),
                        "delta_count": int(_value(entry_fields.get("delta_count"))),
                        "digest_changed": (_label(entry_fields.get("digest_changed")).lower() == "true"),
                    }
                )
            result["equation_section_deltas"] = delta_sections
    context_prob_node = nodes.get("context_probabilities")
    if context_prob_node is not None:
        cp_fields = _fields(context_prob_node)
        result["context_relation_total"] = int(_value(cp_fields.get("relation_total")))
        result["context_context_total"] = int(_value(cp_fields.get("context_total")))
        result["context_goal_total"] = int(_value(cp_fields.get("goal_total")))
        relations_node = cp_fields.get("relations")
        if relations_node is not None and relations_node.kind.name == "LIST":
            relation_entries = []
            for entry in relations_node.args:
                entry_fields = _fields(entry)
                relation_entries.append(
                    {
                        "label": _label(entry_fields.get("label")),
                        "count": int(_value(entry_fields.get("count"))),
                        "probability": _value(entry_fields.get("probability")),
                    }
                )
            result["context_relation_probs"] = relation_entries
        contexts_node = cp_fields.get("contexts")
        if contexts_node is not None and contexts_node.kind.name == "LIST":
            context_entries = []
            for entry in contexts_node.args:
                entry_fields = _fields(entry)
                context_entries.append(
                    {
                        "label": _label(entry_fields.get("label")),
                        "count": int(_value(entry_fields.get("count"))),
                        "probability": _value(entry_fields.get("probability")),
                    }
                )
            result["context_context_probs"] = context_entries
        goals_node = cp_fields.get("goals")
        if goals_node is not None and goals_node.kind.name == "LIST":
            goal_entries = []
            for entry in goals_node.args:
                entry_fields = _fields(entry)
                goal_entries.append(
                    {
                        "label": _label(entry_fields.get("label")),
                        "count": int(_value(entry_fields.get("count"))),
                        "probability": _value(entry_fields.get("probability")),
                    }
                )
            result["context_goal_probs"] = goal_entries
    synthesis_node = nodes.get("meta_synthesis")
    if synthesis_node is not None:
        syn_fields = _fields(synthesis_node)
        plan_total = syn_fields.get("plan_total")
        proof_total = syn_fields.get("proof_total")
        program_total = syn_fields.get("program_total")
        if plan_total is not None:
            result["synthesis_plan_total"] = int(_value(plan_total))
        if proof_total is not None:
            result["synthesis_proof_total"] = int(_value(proof_total))
        if program_total is not None:
            result["synthesis_program_total"] = int(_value(program_total))
        plans_node = syn_fields.get("plans")
        if plans_node is not None and plans_node.kind.name == "LIST":
            plan_entries = []
            for entry in plans_node.args:
                entry_fields = _fields(entry)
                payload: dict[str, object] = {}
                payload["plan_id"] = _label(entry_fields.get("plan_id"))
                source_node = entry_fields.get("source_digest")
                if source_node is not None:
                    payload["source_digest"] = _label(source_node)
                step_node = entry_fields.get("step_count")
                if step_node is not None:
                    payload["step_count"] = int(_value(step_node))
                plan_entries.append(payload)
            result["synthesis_plans"] = plan_entries
        proofs_node = syn_fields.get("proofs")
        if proofs_node is not None and proofs_node.kind.name == "LIST":
            proof_entries = []
            for entry in proofs_node.args:
                entry_fields = _fields(entry)
                proof_entries.append(
                    {
                        "query": _label(entry_fields.get("query")),
                        "truth": _label(entry_fields.get("truth")),
                        "proof_digest": _label(entry_fields.get("proof_digest")),
                    }
                )
            result["synthesis_proofs"] = proof_entries
        programs_node = syn_fields.get("programs")
        if programs_node is not None and programs_node.kind.name == "LIST":
            program_entries = []
            for entry in programs_node.args:
                entry_fields = _fields(entry)
                payload: dict[str, object] = {
                    "language": _label(entry_fields.get("language")),
                    "status": _label(entry_fields.get("status")),
                }
                src_lang = entry_fields.get("source_language")
                if src_lang is not None:
                    payload["source_language"] = _label(src_lang)
                src_digest = entry_fields.get("source_digest")
                if src_digest is not None:
                    payload["source_digest"] = _label(src_digest)
                fn_count = entry_fields.get("function_count")
                if fn_count is not None:
                    payload["function_count"] = int(_value(fn_count))
                program_entries.append(payload)
            result["synthesis_programs"] = program_entries
    proof_node = nodes.get("meta_proof")
    if proof_node is not None:
        proof_fields = _fields(proof_node)
        result["logic_proof_truth"] = _label(proof_fields.get("truth"))
        result["logic_proof_query"] = _label(proof_fields.get("query"))
        result["logic_proof_digest"] = _label(proof_fields.get("proof_digest"))
        proof_payload = proof_fields.get("proof")
        if proof_payload is not None:
            result["logic_proof"] = to_json(proof_payload)
    digest_node = nodes.get("meta_digest")
    if digest_node is not None:
        digest_fields = _fields(digest_node)
        result["meta_digest"] = _label(digest_fields.get("hex"))
    calc_exec_node = nodes.get("meta_calc_exec")
    if calc_exec_node is not None:
        exec_fields = _fields(calc_exec_node)
        result["calc_exec_route"] = _label(exec_fields.get("plan_route"))
        result["calc_exec_description"] = _label(exec_fields.get("plan_description"))
        result["calc_exec_consistent"] = (_label(exec_fields.get("consistent")).lower() == "true")
        result["calc_exec_error"] = _label(exec_fields.get("error"))
        if (answer_node := exec_fields.get("answer")) is not None:
            result["calc_exec_answer"] = to_json(answer_node)
        result["calc_exec_answer_fingerprint"] = _label(exec_fields.get("answer_fingerprint"))
        result["calc_exec_snapshot_digest"] = _label(exec_fields.get("snapshot_digest"))
        snapshot_pc = exec_fields.get("snapshot_pc")
        if snapshot_pc is not None:
            result["calc_exec_snapshot_pc"] = int(_value(snapshot_pc))
        snapshot_depth = exec_fields.get("snapshot_stack_depth")
        if snapshot_depth is not None:
            result["calc_exec_snapshot_stack_depth"] = int(_value(snapshot_depth))
    return result


def _fields(node: Node) -> dict[str, Node]:
    return {key: value for key, value in node.fields}


def _label(node: Node | None) -> str:
    if node is None:
        return ""
    return node.label or ""


def _value(node: Node | None) -> float:
    if node is None:
        return 0.0
    if node.value is not None:
        return float(node.value)
    return 0.0


def _extract_meta_calculation(meta: MetaTransformResult | None) -> Node | None:
    if meta is None or meta.lc_meta is None:
        return None
    fields = _fields(meta.lc_meta)
    calc_node = fields.get("calculus")
    if calc_node is None:
        return None
    return _meta_calc_node(calc_node)


def _direct_answer_plan(route: MetaRoute, answer: Node | None) -> MetaCalculationPlan | None:
    if answer is None:
        return None
    program = Program(
        instructions=[
            Instruction(Opcode.PUSH_CONST, 0),
            Instruction(Opcode.STORE_ANSWER, 0),
            Instruction(Opcode.HALT, 0),
        ],
        constants=[answer],
    )
    description = f"{route.value}_direct_answer"
    return MetaCalculationPlan(route=route, program=program, description=description)


def _text_phi_plan(calculus: MetaCalculation | None = None) -> MetaCalculationPlan:
    opcodes: list[Opcode] = list(text_opcode_pipeline(calculus))
    constants: list[Node] = []
    if calculus is not None:
        opcodes.extend((Opcode.PUSH_CONST, Opcode.STORE_ANSWER))
        constants.append(_calculus_answer_node(calculus))
    opcodes.append(Opcode.HALT)
    instructions = [Instruction(opcode, 0) for opcode in opcodes]
    operator_label = (calculus.operator if calculus else "").lower()
    description = (
        "text_phi_pipeline" if not operator_label else f"text_phi_{operator_label}"
    )
    program = Program(instructions=instructions, constants=constants)
    return MetaCalculationPlan(route=MetaRoute.TEXT, program=program, description=description)


def _calculus_answer_node(calculus: MetaCalculation) -> Node:
    return liu_struct(
        tag=entity("lc_meta_calc"),
        payload=meta_calculation_to_node(calculus),
    )


def _meta_digest_node(nodes: list[Node]) -> Node:
    hasher = blake2b(digest_size=16)
    for node in nodes:
        hasher.update(fingerprint(node).encode("utf-8"))
    return liu_struct(tag=entity("meta_digest"), hex=liu_text(hasher.hexdigest()))


def _meta_proof_node(proof: Node) -> Node:
    fields = _fields(proof)
    truth_node = fields.get("truth") or entity("unknown")
    query_node = fields.get("query") or liu_text("")
    return liu_struct(
        tag=entity("meta_proof"),
        truth=truth_node,
        query=query_node,
        proof=proof,
        proof_digest=liu_text(fingerprint(proof)),
    )


def _meta_calc_exec_node(calc_result: "MetaCalculationResult") -> Node | None:
    fields: dict[str, Node] = {
        "tag": entity("meta_calc_exec"),
        "plan_route": entity(calc_result.plan.route.value),
        "plan_description": entity(calc_result.plan.description),
        "consistent": entity("true" if calc_result.consistent else "false"),
    }
    if calc_result.error:
        fields["error"] = liu_text(calc_result.error)
    if calc_result.answer is not None:
        fields["answer"] = calc_result.answer
        fields["answer_fingerprint"] = entity(fingerprint(calc_result.answer))
    snapshot = calc_result.snapshot
    if snapshot:
        digest = _snapshot_digest(snapshot)
        fields["snapshot_digest"] = liu_text(digest)
        pc = snapshot.get("pc")
        if isinstance(pc, (int, float)):
            fields["snapshot_pc"] = number(pc)
        depth = snapshot.get("stack_depth")
        if isinstance(depth, (int, float)):
            fields["snapshot_stack_depth"] = number(depth)
        if (summary_json := snapshot.get("code_summary")):
            node = _json_to_node(summary_json)
            if node is not None:
                fields["code_summary"] = node
        if (fn_names := snapshot.get("code_summary_functions")):
            fields["code_summary_functions"] = list_node(entity(name) for name in fn_names)
        if (fn_details := snapshot.get("code_summary_function_details")):
            detail_nodes = []
            for entry in fn_details:
                detail_fields: dict[str, Node] = {"name": entity(str(entry.get("name", "")))}
                if entry.get("param_count") is not None:
                    detail_fields["param_count"] = number(int(entry["param_count"]))
                params = entry.get("parameters")
                if params:
                    detail_fields["parameters"] = list_node(entity(str(p)) for p in params)
                detail_nodes.append(liu_struct(**detail_fields))
            if detail_nodes:
                fields["code_summary_function_details"] = list_node(detail_nodes)
    return liu_struct(**fields)


def _snapshot_digest(snapshot: dict[str, Any]) -> str:
    serialized = json.dumps(snapshot, sort_keys=True, separators=(",", ":"))
    return blake2b(serialized.encode("utf-8"), digest_size=16).hexdigest()


def _json_to_node(payload: dict[str, Any]) -> Node | None:
    try:
        return from_json(json.dumps(payload))
    except Exception:
        return None


def _maybe_state_followup(
    calculus: MetaCalculation | None, term: LCTerm | None, has_memory: bool
) -> MetaCalculation | None:
    if not has_memory:
        return calculus
    if calculus is None:
        if term is None:
            return MetaCalculation(operator="STATE_FOLLOWUP", operands=tuple())
        return MetaCalculation(operator="STATE_FOLLOWUP", operands=(term,))
    follow_map = {
        "STATE_QUERY": "STATE_FOLLOWUP",
        "STATE_ASSERT": "STATE_FOLLOWUP",
        "STATE_FOLLOWUP": "STATE_FOLLOWUP",
        "FACT_QUERY": "FACT_FOLLOWUP",
        "FACT_FOLLOWUP": "FACT_FOLLOWUP",
        "COMMAND_ROUTE": "COMMAND_FOLLOWUP",
        "COMMAND_FOLLOWUP": "COMMAND_FOLLOWUP",
    }
    target = follow_map.get(calculus.operator)
    if target:
        return MetaCalculation(operator=target, operands=calculus.operands)
    return calculus
