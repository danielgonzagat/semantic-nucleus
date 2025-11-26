"""
Acoplamento entre o instinto IAN-Ω e o núcleo LIU/NSR.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Tuple

from liu import entity, list_node, number, struct, text, Node

from .ian import DEFAULT_INSTINCT, IANInstinct, ReplyPlan, Utterance


@dataclass(frozen=True)
class InstinctHook:
    instinct: IANInstinct
    utterance: Utterance
    reply_plan: ReplyPlan
    struct_node: Node
    answer_node: Node
    context_nodes: Tuple[Node, ...]
    quality: float


def maybe_route_text(text_value: str, instinct: IANInstinct | None = None) -> InstinctHook | None:
    instinct = instinct or DEFAULT_INSTINCT
    utterance = instinct.analyze(text_value)
    if utterance.role == "UNKNOWN":
        return None
    reply_plan = instinct.plan_reply(utterance)
    struct_node = utterance_to_struct(utterance)
    rendered = instinct.render(reply_plan)
    answer_node = reply_plan_to_answer(reply_plan, instinct, rendered)
    context_nodes = context_nodes_for_interaction(utterance, reply_plan, rendered, instinct)
    return InstinctHook(
        instinct=instinct,
        utterance=utterance,
        reply_plan=reply_plan,
        struct_node=struct_node,
        answer_node=answer_node,
        context_nodes=context_nodes,
        quality=0.85,
    )


def utterance_to_struct(utterance: Utterance) -> Node:
    """
    Converte uma fala reconhecida pelo IAN em STRUCT LIU auditável.
    """

    token_nodes = tuple(_token_struct(token) for token in utterance.tokens)
    return struct(
        intent=entity(utterance.role.lower()),
        semantics=entity(utterance.semantics.lower()),
        language=entity(utterance.language),
        tokens=list_node(token_nodes),
    )


def reply_plan_to_answer(
    plan: ReplyPlan, instinct: IANInstinct | None = None, rendered: str | None = None
) -> Node:
    """
    Constrói STRUCT de resposta com texto renderizado + códigos numéricos.
    """

    instinct = instinct or DEFAULT_INSTINCT
    rendered = rendered or instinct.render(plan)
    token_nodes = tuple(_plan_token_struct(surface, codes) for surface, codes in zip(plan.tokens, plan.token_codes))
    return struct(
        answer=text(rendered),
        plan_role=entity(plan.role.lower()),
        plan_semantics=entity(plan.semantics.lower()),
        plan_language=entity(plan.language),
        plan_tokens=list_node(token_nodes),
    )


def context_nodes_for_interaction(
    utterance: Utterance,
    plan: ReplyPlan,
    rendered: str,
    instinct: IANInstinct | None = None,
) -> Tuple[Node, ...]:
    instinct = instinct or DEFAULT_INSTINCT
    utter_tokens = tuple(_token_struct(token) for token in utterance.tokens)
    plan_tokens = tuple(_plan_token_struct(surface, codes) for surface, codes in zip(plan.tokens, plan.token_codes))
    utter_struct = struct(
        tag=entity("ian_utterance"),
        intent=entity(utterance.role.lower()),
        semantics=entity(utterance.semantics.lower()),
        tokens=list_node(utter_tokens),
    )
    reply_struct = struct(
        tag=entity("ian_reply"),
        plan_role=entity(plan.role.lower()),
        plan_semantics=entity(plan.semantics.lower()),
        plan_language=entity(plan.language),
        answer=text(rendered),
        plan_tokens=list_node(plan_tokens),
    )
    return (utter_struct, reply_struct)


def _token_struct(token) -> Node:
    fields: dict[str, Node] = {
        "surface": text(token.surface),
        "normalized": text(token.normalized),
        "codes": list_node(_codes_to_numbers(token.codes)),
    }
    if token.lexeme:
        fields["semantics"] = entity(token.lexeme.semantics.lower())
        fields["pos"] = entity(token.lexeme.pos.lower())
    return struct(**fields)


def _plan_token_struct(surface: str, codes: Iterable[int]) -> Node:
    return struct(
        surface=text(surface),
        codes=list_node(_codes_to_numbers(codes)),
    )


def _codes_to_numbers(codes: Iterable[int]):
    return tuple(number(code) for code in codes)


__all__ = [
    "InstinctHook",
    "maybe_route_text",
    "utterance_to_struct",
    "reply_plan_to_answer",
    "context_nodes_for_interaction",
]
