"""
Constructs meta_synthesis nodes summarizing Φ synthesis outputs.
"""

from __future__ import annotations

from typing import Dict, Tuple

from liu import Node, NodeKind, entity, list_node, number, struct as liu_struct


def build_meta_synthesis(context: Tuple[Node, ...]) -> Node | None:
    plan_entries = tuple(_plan_entry(node) for node in context if _tag(node) == "synth_plan")
    proof_entries = tuple(_proof_entry(node) for node in context if _tag(node) == "synth_proof")
    program_entries = tuple(_program_entry(node) for node in context if _tag(node) == "synth_prog")
    if not plan_entries and not proof_entries and not program_entries:
        return None
    fields: Dict[str, Node] = {
        "tag": entity("meta_synthesis"),
        "plan_total": number(len(plan_entries)),
        "proof_total": number(len(proof_entries)),
        "program_total": number(len(program_entries)),
    }
    if plan_entries:
        fields["plans"] = list_node(plan_entries)
    if proof_entries:
        fields["proofs"] = list_node(proof_entries)
    if program_entries:
        fields["programs"] = list_node(program_entries)
    return liu_struct(**fields)


def _tag(node: Node) -> str:
    if node.kind is not NodeKind.STRUCT:
        return ""
    tag_field = dict(node.fields).get("tag")
    return (tag_field.label or "").lower() if tag_field else ""


def _plan_entry(node: Node) -> Node:
    fields = dict(node.fields)
    plan_id = fields.get("plan_id")
    step_count = fields.get("step_count")
    source_digest = fields.get("source_digest")
    summary_fields: Dict[str, Node] = {
        "tag": entity("synth_plan_entry"),
    }
    if plan_id is not None:
        summary_fields["plan_id"] = plan_id
    if step_count is not None:
        summary_fields["step_count"] = step_count
    if source_digest is not None:
        summary_fields["source_digest"] = source_digest
    return liu_struct(**summary_fields)


def _proof_entry(node: Node) -> Node:
    fields = dict(node.fields)
    query = fields.get("query")
    truth = fields.get("truth")
    proof_digest = fields.get("proof_digest")
    summary_fields: Dict[str, Node] = {
        "tag": entity("synth_proof_entry"),
    }
    if query is not None:
        summary_fields["query"] = query
    if truth is not None:
        summary_fields["truth"] = truth
    if proof_digest is not None:
        summary_fields["proof_digest"] = proof_digest
    return liu_struct(**summary_fields)


def _program_entry(node: Node) -> Node:
    fields = dict(node.fields)
    summary_fields: Dict[str, Node] = {
        "tag": entity("synth_prog_entry"),
    }
    if "language" in fields:
        summary_fields["language"] = fields["language"]
    if "status" in fields:
        summary_fields["status"] = fields["status"]
    if "source_language" in fields:
        summary_fields["source_language"] = fields["source_language"]
    if "source_digest" in fields:
        summary_fields["source_digest"] = fields["source_digest"]
    function_count = fields.get("function_count")
    if function_count is not None:
        summary_fields["function_count"] = function_count
    return liu_struct(**summary_fields)


__all__ = ["build_meta_synthesis"]
