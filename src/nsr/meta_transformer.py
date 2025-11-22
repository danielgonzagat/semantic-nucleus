"""
Meta-Transformador: converte entradas cruas em meta-representações LIU auditáveis.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Tuple

from liu import Node, struct as liu_struct, entity, text as liu_text, number

from .code_bridge import maybe_route_code
from .ian_bridge import maybe_route_text
from .lex import DEFAULT_LEXICON, tokenize
from .logic_bridge import maybe_route_logic
from .math_bridge import maybe_route_math
from .parser import build_struct
from .state import SessionCtx
from .meta_structures import maybe_build_lc_meta_struct
from .lc_omega import MetaCalculation
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

        math_hook = maybe_route_math(text_value)
        if math_hook:
            plan = _direct_answer_plan(MetaRoute.MATH, math_hook.answer_node)
            self.session.language_hint = math_hook.reply.language
            return MetaTransformResult(
                struct_node=math_hook.struct_node,
                route=MetaRoute.MATH,
                input_text=text_value,
                trace_label=f"MATH[{math_hook.utterance.role}]",
                preseed_answer=math_hook.answer_node,
                preseed_context=self._with_meta_context(
                    math_hook.context_nodes,
                    MetaRoute.MATH,
                    math_hook.reply.language,
                    text_value,
                ),
                preseed_quality=math_hook.quality,
                language_hint=math_hook.reply.language,
                calc_plan=plan,
            )

        logic_hook = maybe_route_logic(text_value, engine=self.session.logic_engine)
        if logic_hook:
            plan = _direct_answer_plan(MetaRoute.LOGIC, logic_hook.answer_node)
            self.session.logic_engine = logic_hook.result.engine
            self.session.logic_serialized = logic_hook.snapshot
            return MetaTransformResult(
                struct_node=logic_hook.struct_node,
                route=MetaRoute.LOGIC,
                input_text=text_value,
                trace_label=logic_hook.trace_label,
                preseed_answer=logic_hook.answer_node,
                preseed_context=self._with_meta_context(
                    logic_hook.context_nodes,
                    MetaRoute.LOGIC,
                    self.session.language_hint,
                    text_value,
                ),
                preseed_quality=logic_hook.quality,
                calc_plan=plan,
            )

        code_hook = maybe_route_code(text_value)
        if code_hook:
            plan = _direct_answer_plan(MetaRoute.CODE, code_hook.answer_node)
            return MetaTransformResult(
                struct_node=code_hook.struct_node,
                route=MetaRoute.CODE,
                input_text=text_value,
                trace_label=code_hook.trace_label,
                preseed_answer=code_hook.answer_node,
                preseed_context=self._with_meta_context(
                    code_hook.context_nodes,
                    MetaRoute.CODE,
                    code_hook.language,
                    text_value,
                ),
                preseed_quality=code_hook.quality,
                language_hint=code_hook.language,
                calc_plan=plan,
            )

        instinct_hook = maybe_route_text(text_value)
        if instinct_hook:
            plan = _direct_answer_plan(MetaRoute.INSTINCT, instinct_hook.answer_node)
            self.session.language_hint = instinct_hook.reply_plan.language
            return MetaTransformResult(
                struct_node=instinct_hook.struct_node,
                route=MetaRoute.INSTINCT,
                input_text=text_value,
                trace_label=f"IAN[{instinct_hook.utterance.role}]",
                preseed_answer=instinct_hook.answer_node,
                preseed_context=self._with_meta_context(
                    instinct_hook.context_nodes,
                    MetaRoute.INSTINCT,
                    instinct_hook.reply_plan.language,
                    text_value,
                ),
                preseed_quality=instinct_hook.quality,
                language_hint=instinct_hook.reply_plan.language,
                calc_plan=plan,
            )

        language = (self.session.language_hint or "pt").lower()
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
        )
        if lc_meta_node is not None:
            meta_context = tuple((*meta_context, lc_meta_node))
        return MetaTransformResult(
            struct_node=struct_node,
            route=MetaRoute.TEXT,
            input_text=text_value,
            preseed_context=meta_context,
            language_hint=language,
            calc_plan=text_plan,
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
    ) -> Tuple[Node, ...]:
        route_node = _meta_route_node(route, language)
        input_node = _meta_input_node(text_value)
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


def build_meta_summary(
    meta: MetaTransformResult,
    answer_text: str,
    quality: float,
    halt_reason: str,
) -> Tuple[Node, ...]:
    return (
        _meta_route_node(meta.route, meta.language_hint),
        _meta_input_node(meta.input_text),
        _meta_output_node(answer_text, quality, halt_reason),
    )


def meta_summary_to_dict(summary: Tuple[Node, ...]) -> dict[str, object]:
    nodes = {dict(node.fields)["tag"].label: node for node in summary}
    route_fields = _fields(nodes["meta_route"])
    input_fields = _fields(nodes["meta_input"])
    output_fields = _fields(nodes["meta_output"])
    return {
        "route": _label(route_fields["route"]),
        "language": _label(route_fields.get("language")),
        "input_size": _value(input_fields["size"]),
        "input_preview": _label(input_fields["preview"]),
        "answer": _label(output_fields["answer"]),
        "quality": _value(output_fields["quality"]),
        "halt": _label(output_fields["halt"]),
    }


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


_TEXT_PIPELINES: dict[str, Tuple[Opcode, ...]] = {
    "STATE_QUERY": (Opcode.PHI_NORMALIZE, Opcode.PHI_INFER, Opcode.PHI_SUMMARIZE),
    "STATE_ASSERT": (Opcode.PHI_NORMALIZE, Opcode.PHI_ANSWER, Opcode.PHI_EXPLAIN, Opcode.PHI_SUMMARIZE),
    "FACT_QUERY": (Opcode.PHI_NORMALIZE, Opcode.PHI_INFER, Opcode.PHI_SUMMARIZE),
    "COMMAND_ROUTE": (Opcode.PHI_NORMALIZE, Opcode.PHI_INFER, Opcode.PHI_SUMMARIZE),
    "EMIT_GREETING": (Opcode.PHI_NORMALIZE, Opcode.PHI_SUMMARIZE),
    "EMIT_THANKS": (Opcode.PHI_NORMALIZE, Opcode.PHI_SUMMARIZE),
    "EMIT_FAREWELL": (Opcode.PHI_NORMALIZE, Opcode.PHI_SUMMARIZE),
    "EMIT_CONFIRM": (Opcode.PHI_NORMALIZE, Opcode.PHI_SUMMARIZE),
}
_DEFAULT_TEXT_PIPELINE: Tuple[Opcode, ...] = (Opcode.PHI_NORMALIZE, Opcode.PHI_SUMMARIZE)


def _text_phi_plan(calculus: MetaCalculation | None = None) -> MetaCalculationPlan:
    operator = (calculus.operator if calculus else "").upper()
    pipeline = _TEXT_PIPELINES.get(operator, _DEFAULT_TEXT_PIPELINE)
    instructions = [Instruction(opcode, 0) for opcode in (*pipeline, Opcode.HALT)]
    description = (
        "text_phi_pipeline" if not operator else f"text_phi_{operator.lower()}"
    )
    program = Program(instructions=instructions, constants=[])
    return MetaCalculationPlan(route=MetaRoute.TEXT, program=program, description=description)
