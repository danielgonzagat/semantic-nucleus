"""
Assinaturas de relações e operadores da LIU núcleo.
"""

from __future__ import annotations

from typing import Dict

from .kinds import Signature, Sort

REL_SIGNATURES: Dict[str, Signature] = {}
OP_SIGNATURES: Dict[str, Signature] = {}


def _rel(name: str, *args: Sort, returns: Sort = Sort.PROP) -> None:
    """Register a relation signature."""

    REL_SIGNATURES[name] = Signature(name=name, args=tuple(args), returns=returns)


def _op(name: str, returns: Sort, *args: Sort) -> None:
    """Register an operator signature."""

    OP_SIGNATURES[name] = Signature(name=name, args=tuple(args), returns=returns)


def _bootstrap() -> None:
    # Core ontology relations
    _rel("IS_A", Sort.THING, Sort.TYPE)
    _rel("INSTANCE_OF", Sort.THING, Sort.TYPE)
    _rel("TYPE", Sort.THING, Sort.TYPE)
    _rel("PART_OF", Sort.THING, Sort.THING)
    _rel("HAS_PART", Sort.THING, Sort.THING)
    _rel("HAS", Sort.THING, Sort.THING)
    _rel("CAUSE", Sort.EVENT, Sort.EVENT)
    _rel("EFFECT", Sort.EVENT, Sort.EVENT)
    _rel("BEFORE", Sort.EVENT, Sort.EVENT)
    _rel("AFTER", Sort.EVENT, Sort.EVENT)
    _rel("EQUAL", Sort.THING, Sort.THING)
    _rel("DIFFERENT", Sort.THING, Sort.THING)
    _rel("DESCRIBES", Sort.CONTEXT, Sort.THING, returns=Sort.PROP)

    # Code relations (namespace code@1)
    _rel("code/MODULE", Sort.CODE, Sort.STATE)
    _rel("code/DEFN", Sort.CODE, Sort.STATE)
    _rel("code/CLAUSE", Sort.CODE, Sort.STATE)
    _rel("code/PARAM", Sort.CODE, Sort.STATE)
    _rel("code/RETURNS", Sort.CODE, Sort.TYPE)
    _rel("code/CALL", Sort.CODE, Sort.CODE, Sort.STATE)
    _rel("code/ASSIGN", Sort.STATE, Sort.STATE)
    _rel("code/IF", Sort.STATE, Sort.STATE, Sort.STATE)
    _rel("code/LOOP", Sort.STATE, Sort.STATE, Sort.STATE)
    _rel("code/MATCH", Sort.STATE, Sort.STATE)
    _rel("code/BORROW", Sort.CODE, Sort.TEXT, Sort.TEXT)
    _rel("code/MOVE", Sort.CODE)
    _rel("code/TYPE", Sort.CODE, Sort.TYPE)
    _rel("code/ANNOTATION", Sort.CODE, Sort.STATE)

    # Operator signatures (Φ-set + utilities)
    _op("NORMALIZE", Sort.STATE, Sort.STATE)
    _op("EXTRACT", Sort.ANY, Sort.STRUCTURE, Sort.TEXT)
    _op("COMPARE", Sort.PROP, Sort.ANY, Sort.ANY)
    _op("INFER", Sort.STATE, Sort.STATE)
    _op("MAP", Sort.LIST, Sort.LIST, Sort.OPERATOR)
    _op("REDUCE", Sort.ANY, Sort.LIST, Sort.OPERATOR)
    _op("REWRITE", Sort.ANY, Sort.ANY)
    _op("EXPAND", Sort.STATE, Sort.ANY)
    _op("ANSWER", Sort.ANSWER, Sort.ANY)
    _op("EXPLAIN", Sort.ANSWER, Sort.STATE, Sort.ANY)
    _op("SUMMARIZE", Sort.ANSWER, Sort.STATE)
    _op("ALIGN", Sort.STATE, Sort.STATE)
    _op("STABILIZE", Sort.STATE, Sort.STATE)
    _op("code/EVAL_PURE", Sort.ANY, Sort.ANY)


_bootstrap()


__all__ = ["REL_SIGNATURES", "OP_SIGNATURES"]
