"""
Core ontological facts for the LIU/NSR pipeline.
"""

from __future__ import annotations

from liu import relation, entity

CORE_V1 = (
    relation("IS_A", entity("carro"), entity("type::veiculo")),
    relation("IS_A", entity("moto"), entity("type::veiculo")),
    relation("IS_A", entity("veiculo"), entity("type::coisa")),
    relation("IS_A", entity("roda"), entity("type::componente")),
    relation("PART_OF", entity("roda"), entity("carro")),
    relation("HAS_PART", entity("carro"), entity("roda")),
    relation("HAS", entity("motor"), entity("energia")),
    relation("CAUSE", entity("event::mover"), entity("event::deslocamento")),
    relation("DESCRIBES", entity("context::transporte"), entity("carro")),
)


def facts() -> tuple:
    """Return tuple copy to avoid mutation."""

    return CORE_V1


__all__ = ["CORE_V1", "facts"]
