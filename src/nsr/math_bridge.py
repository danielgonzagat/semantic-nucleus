"""
Acoplamento entre o MathInstinct e o núcleo LIU/NSR.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

from liu import entity, number, struct, text, Node

from .math_instinct import MathInstinct, MathReply, MathUtterance


@dataclass(frozen=True, slots=True)
class MathHook:
    instinct: MathInstinct
    utterance: MathUtterance
    reply: MathReply
    struct_node: Node
    answer_node: Node
    context_nodes: Tuple[Node, ...]
    quality: float


def maybe_route_math(text_value: str, instinct: MathInstinct | None = None) -> MathHook | None:
    instinct = instinct or MathInstinct()
    reply = instinct.evaluate(text_value)
    if reply is None:
        return None
    utterance = instinct.analyze(text_value)
    if utterance is None:
        return None
    struct_node = _utterance_struct(utterance)
    answer_node = _reply_struct(reply)
    context_nodes = (
        struct(tag=entity("math_utterance"), expression=text(utterance.expression), language=entity(utterance.language)),
        struct(tag=entity("math_reply"), answer=text(reply.text), value=number(reply.value), language=entity(reply.language)),
    )
    return MathHook(
        instinct=instinct,
        utterance=utterance,
        reply=reply,
        struct_node=struct_node,
        answer_node=answer_node,
        context_nodes=context_nodes,
        quality=0.92,
    )


def _utterance_struct(utterance: MathUtterance) -> Node:
    return struct(
        intent=entity(utterance.role.lower()),
        language=entity(utterance.language),
        expression=text(utterance.expression),
        original=text(utterance.original),
    )


def _reply_struct(reply: MathReply) -> Node:
    return struct(
        answer=text(reply.text),
        value=number(reply.value),
        plan_role=entity("math_eval"),
        plan_language=entity(reply.language),
    )


__all__ = ["MathHook", "maybe_route_math"]
