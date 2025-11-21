"""
Code ontology describing language metadata and canonical module facts.
"""

from __future__ import annotations

from liu import relation, entity, struct, text, list_node

CODE_V1 = (
    relation(
        "code/ANNOTATION",
        entity("code/lang::python"),
        struct(language=text("python"), version=text("3.11"), typing=text("dynamic")),
    ),
    relation(
        "code/ANNOTATION",
        entity("code/lang::elixir"),
        struct(language=text("elixir"), version=text("1.16"), typing=text("dynamic")),
    ),
    relation(
        "code/ANNOTATION",
        entity("code/lang::rust"),
        struct(language=text("rust"), version=text("1.78"), typing=text("static")),
    ),
    relation(
        "code/ANNOTATION",
        entity("code/lang::logic"),
        struct(language=text("logic"), version=text("prolog-lite"), typing=text("logical")),
    ),
    relation(
        "code/MODULE",
        entity("code/mod::stdlib"),
        struct(name=entity("stdlib"), body=list_node([])),
    ),
)


def facts() -> tuple:
    return CODE_V1


__all__ = ["CODE_V1", "facts"]
