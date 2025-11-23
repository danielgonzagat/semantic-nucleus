"""
Meta-Expressar: sintetiza respostas LIU e referências de raciocínio em estruturas auditáveis.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from liu import (
    Node,
    entity,
    number,
    list_node,
    struct as liu_struct,
    text as liu_text,
    fingerprint,
    to_json,
)

from .meta_transformer import MetaRoute


@dataclass(frozen=True, slots=True)
class MetaExpressionConfig:
    preview_limit: int = 160


def build_meta_expression(
    answer: Node | None,
    *,
    reasoning: Node | None,
    quality: float,
    halt_reason: str,
    route: MetaRoute | None,
    language: str | None,
    memory_refs: tuple[Node, ...] | None = None,
    config: MetaExpressionConfig | None = None,
) -> Node | None:
    """
    Constrói um nó LIU com metadados de expressão (Meta-Expressar).
    """

    if answer is None or not answer.fields:
        return None
    cfg = config or MetaExpressionConfig()
    preview = _answer_preview(answer, limit=cfg.preview_limit)
    fields: dict[str, Node] = {
        "tag": entity("meta_expression"),
        "preview": liu_text(preview),
        "quality": number(round(float(max(0.0, min(1.0, quality))), 6)),
        "halt": entity((halt_reason or "").lower()),
        "answer_digest": entity(fingerprint(answer)),
        "answer": answer,
    }
    if route is not None:
        fields["route"] = entity(route.value)
    if language:
        fields["language"] = entity(language)
    if reasoning is not None:
        reasoning_digest = _extract_reasoning_digest(reasoning)
        if reasoning_digest:
            fields["reasoning_digest"] = liu_text(reasoning_digest)
    memory_context_nodes = _memory_context(memory_refs)
    if memory_context_nodes:
        fields["memory_context"] = list_node(memory_context_nodes)
    return liu_struct(**fields)


def _answer_preview(answer: Node, *, limit: int) -> str:
    payload = dict(answer.fields).get("answer") if answer.fields else None
    node = payload or answer
    label = (node.label or "").strip()
    if not label and node.kind.name == "TEXT" and node.value is not None:
        label = str(node.value)
    if not label:
        label = to_json(node)
    label = label.replace("\n", " ").strip()
    if not label:
        label = fingerprint(node)
    if len(label) > limit:
        return label[: limit - 3] + "..."
    return label


def _extract_reasoning_digest(reasoning: Node) -> Optional[str]:
    fields = dict(reasoning.fields)
    digest_node = fields.get("digest")
    if digest_node and (digest_node.label or ""):
        return digest_node.label
    return fingerprint(reasoning)


def _memory_context(memory_refs: tuple[Node, ...] | None) -> list[Node]:
    if not memory_refs:
        return []
    context: list[Node] = []
    for node in memory_refs:
        fields = dict(node.fields)
        entries = fields.get("entries")
        if entries is None or entries.kind.name != "LIST":
            continue
        for entry in entries.args:
            summary_fields = dict(entry.fields)
            preview = summary_fields.get("answer_preview")
            if preview is None or not preview.label:
                continue
            context.append(
                liu_struct(
                    route=summary_fields.get("route") or entity("text"),
                    preview=preview,
                    reasoning=summary_fields.get("reasoning_digest") or liu_text(""),
                    expression=summary_fields.get("expression_digest") or liu_text(""),
                )
            )
            if len(context) >= 4:
                return context
    return context


__all__ = ["build_meta_expression", "MetaExpressionConfig"]
