"""
Meta-Transformador: converte entradas cruas em meta-representações LIU auditáveis.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from hashlib import blake2b
from typing import Tuple

from liu import (
    Node,
    struct as liu_struct,
    entity,
    text as liu_text,
    number,
    to_json,
    list_node,
    fingerprint,
)

from .code_bridge import maybe_route_code
from .ian_bridge import maybe_route_text
from .lex import DEFAULT_LEXICON, tokenize
from .logic_bridge import maybe_route_logic
from .math_bridge import maybe_route_math
from .parser import build_struct
from .state import SessionCtx
from .meta_structures import maybe_build_lc_meta_struct, meta_calculation_to_node
from .language_detector import detect_language_profile, language_profile_to_node
from .code_ast import build_python_ast_meta
from .lc_omega import MetaCalculation
from .meta_calculus_router import text_opcode_pipeline, text_operation_pipeline
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
    math_ast: Node | None = None


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

        math_hook = maybe_route_math(text_value)
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

        code_hook = maybe_route_code(text_value)
        if code_hook:
            plan = _direct_answer_plan(MetaRoute.CODE, code_hook.answer_node)
            preseed_context = self._with_meta_context(
                code_hook.context_nodes,
                MetaRoute.CODE,
                code_hook.language,
                text_value,
                language_profile_node,
            )
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
        if lc_meta_node is not None:
            struct_node = _set_struct_field(struct_node, "lc_meta", lc_meta_node, overwrite=False)
        text_plan = _text_phi_plan(calculus=lc_parsed.calculus if lc_parsed else None)
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
        fallback_code_ast = None
        if should_build_code_ast:
            fallback_code_ast = build_python_ast_meta(text_value)
            if fallback_code_ast is not None:
                meta_context = tuple((*meta_context, fallback_code_ast))
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
            meta_calculation=lc_parsed.calculus if lc_parsed else None,
            phi_plan_ops=phi_plan_ops,
            language_profile=language_profile_node,
            code_ast=fallback_code_ast,
            math_ast=None,
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
    if meta.math_ast is not None:
        nodes.append(meta.math_ast)
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
