"""
Ontologia mínima embarcada para bootstrapping do ISR.
"""

from __future__ import annotations

from .nodes import Node, entity, relation

BASE_ONTOLOGY: tuple[Node, ...] = (
    relation("IS_A", entity("carro"), entity("veiculo")),
    relation("IS_A", entity("moto"), entity("veiculo")),
    relation("PART_OF", entity("roda"), entity("carro")),
)


__all__ = ["BASE_ONTOLOGY"]
