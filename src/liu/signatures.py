"""
Assinaturas de relações e operadores da LIU núcleo.
"""

from __future__ import annotations

from typing import Dict, Tuple

from .kinds import Signature, Sort

REL_SIGNATURES: Dict[str, Signature] = {}
OP_SIGNATURES: Dict[str, Signature] = {}


def _rel(name: str, *args: Sort) -> None:
    REL_SIGNATURES[name] = Signature(name=name, args=args, returns=Sort.PROP)


def _op(name: str, returns: Sort, *args: Sort) -> None:
    OP_SIGNATURES[name] = Signature(name=name, args=args, returns=returns)


def _bootstrap() -> None:
    _rel("IS_A", Sort.THING, Sort.TYPE)
    _rel("PART_OF", Sort.THING, Sort.THING)
    _rel("HAS", Sort.THING, Sort.THING)
    _rel("CAUSE", Sort.THING, Sort.THING)
    _rel("EFFECT", Sort.THING, Sort.THING)
    _rel("BEFORE", Sort.THING, Sort.THING)
    _rel("AFTER", Sort.THING, Sort.THING)
    _rel("EQUAL", Sort.THING, Sort.THING)
    _rel("DIFFERENT", Sort.THING, Sort.THING)
    _rel("TYPE", Sort.THING, Sort.TYPE)
    _rel("code/DEFN", Sort.THING, Sort.STATE)
    _rel("code/PARAM", Sort.THING, Sort.THING)
    _rel("code/RETURNS", Sort.THING, Sort.TYPE)

    _op("NORMALIZE", Sort.STATE, Sort.STATE)
    _op("EXTRACT", Sort.CONTEXT, Sort.STATE, Sort.TEXT)
    _op("COMPARE", Sort.PROP, Sort.ANY, Sort.ANY)
    _op("INFER", Sort.STATE, Sort.STATE)
    _op("MAP", Sort.LIST, Sort.LIST, Sort.OPERATOR)
    _op("REDUCE", Sort.ANY, Sort.LIST, Sort.OPERATOR)
    _op("REWRITE", Sort.ANY, Sort.ANY)
    _op("EXPAND", Sort.ANY, Sort.ANY)
    _op("ANSWER", Sort.ANSWER, Sort.ANY)
    _op("SUMMARIZE", Sort.ANSWER, Sort.STATE)
    _op("EXPLAIN", Sort.ANSWER, Sort.STATE, Sort.ANY)
    _op("code/EVAL_PURE", Sort.ANY, Sort.ANY)


_bootstrap()


__all__ = ["REL_SIGNATURES", "OP_SIGNATURES"]
