"""
Construtores LIU para snapshots de Equação (meta-auditoria do ISR).
"""

from __future__ import annotations

from liu import Node, entity, number, struct as liu_struct, list_node, text as liu_text

from .equation import EquationSnapshot


def build_meta_equation_node(snapshot: EquationSnapshot) -> Node:
    """
    Serializa `EquationSnapshot` em um nó `meta_equation` auditável.
    """

    stats = snapshot.stats()
    section_specs = [
        ("ontology", stats.ontology),
        ("relations", stats.relations),
        ("context", stats.context),
        ("goals", stats.goals),
        ("ops_queue", stats.ops_queue),
    ]
    section_nodes = [
        liu_struct(
            tag=entity("equation_section"),
            name=entity(name),
            count=number(section.count),
            digest=liu_text(section.digest),
        )
        for name, section in section_specs
    ]
    return liu_struct(
        tag=entity("meta_equation"),
        digest=liu_text(stats.equation_digest),
        input_digest=liu_text(stats.input_digest),
        answer_digest=liu_text(stats.answer_digest),
        quality=number(round(float(stats.quality), 6)),
        sections=list_node(section_nodes),
    )


__all__ = ["build_meta_equation_node"]
