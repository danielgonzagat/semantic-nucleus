"""
Meta-Memória: síntese determinística do histórico recente de meta-summaries.
"""

from __future__ import annotations

from hashlib import blake2b
from typing import Mapping, Sequence

from liu import Node, entity, list_node, number, struct as liu_struct, text as liu_text

from .meta_transformer import meta_summary_to_dict


def build_meta_memory(
    history: Sequence[tuple[Node, ...]],
    current_entry: Mapping[str, object],
    *,
    limit: int = 4,
) -> Node | None:
    """
    Constrói um nó `meta_memory` descrevendo os últimos meta-resultados.
    """

    if limit <= 0:
        return None
    recent = history[-max(0, limit - 1) :]
    entries = []
    position = 0
    for summary in recent:
        data = meta_summary_to_dict(summary)
        entry = _entry_from_mapping(data, position)
        if entry is not None:
            entries.append(entry)
            position += 1
    current = _entry_from_mapping(current_entry, position)
    if current is not None:
        entries.append(current)
    if not entries:
        return None
    digest = blake2b(digest_size=16)
    for entry in entries:
        fields = dict(entry.fields)
        digest.update((fields.get("route").label or "").encode("utf-8"))
        digest.update((fields.get("answer_preview").label or "").encode("utf-8"))
        digest.update((fields.get("reasoning_digest").label or "").encode("utf-8"))
        digest.update((fields.get("expression_digest").label or "").encode("utf-8"))
        equation_digest_node = fields.get("equation_digest")
        equation_trend_node = fields.get("equation_trend")
        digest.update(((equation_digest_node.label if equation_digest_node else "")).encode("utf-8"))
        digest.update(((equation_trend_node.label if equation_trend_node else "")).encode("utf-8"))
        proof_digest_node = fields.get("logic_proof_digest")
        digest.update(((proof_digest_node.label if proof_digest_node else "")).encode("utf-8"))
    return liu_struct(
        tag=entity("meta_memory"),
        size=number(len(entries)),
        entries=list_node(entries),
        digest=liu_text(digest.hexdigest()),
    )


def _entry_from_mapping(payload: Mapping[str, object], position: int) -> Node | None:
    route = str(payload.get("route") or "unknown")
    preview = str(payload.get("expression_preview") or payload.get("answer") or "")
    reasoning_digest = str(
        payload.get("reasoning_trace_digest") or payload.get("reasoning_digest") or ""
    )
    expression_digest = str(
        payload.get("expression_answer_digest") or payload.get("answer_digest") or ""
    )
    equation_digest = str(payload.get("equation_digest") or "")
    equation_trend = str(payload.get("equation_trend") or "")
    equation_quality = str(payload.get("equation_quality") or "")
    equation_delta_quality = str(payload.get("equation_delta_quality") or "")
    proof_truth = str(payload.get("logic_proof_truth") or "")
    proof_query = str(payload.get("logic_proof_query") or "")
    proof_digest = str(payload.get("logic_proof_digest") or "")
    if not preview and not expression_digest and not reasoning_digest and not equation_digest:
        return None
    fields = {
        "tag": entity("memory_entry"),
        "position": number(position),
        "route": entity(route),
        "answer_preview": liu_text(preview),
        "reasoning_digest": liu_text(reasoning_digest),
        "expression_digest": liu_text(expression_digest),
    }
    if equation_digest:
        fields["equation_digest"] = liu_text(equation_digest)
    if equation_trend:
        fields["equation_trend"] = liu_text(equation_trend)
    if equation_quality:
        fields["equation_quality"] = liu_text(equation_quality)
    if equation_delta_quality:
        fields["equation_delta_quality"] = liu_text(equation_delta_quality)
    if proof_truth:
        fields["logic_proof_truth"] = liu_text(proof_truth)
    if proof_query:
        fields["logic_proof_query"] = liu_text(proof_query)
    if proof_digest:
        fields["logic_proof_digest"] = liu_text(proof_digest)
    return liu_struct(**fields)


__all__ = ["build_meta_memory"]
