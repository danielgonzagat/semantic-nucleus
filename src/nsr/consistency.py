"""
Ferramentas de consistência estrutural para o NSR.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Tuple

from liu import Node, NodeKind
from liu.hash import fingerprint

Signature = Tuple[str, Tuple[str, ...], Tuple[Tuple[str, str], ...], str | None]

_NEGATION_PREFIXES = ("NOT_", "NO_", "NAO_", "NON_", "WITHOUT_", "SEM_", "ANTI_", "!")
_NEGATION_SUFFIXES = ("_NOT", "_NO", "_NAO", "_NON", "_NEG", "_LESS")


@dataclass(frozen=True)
class Contradiction:
    """Representa um par positivo/negativo incompatível."""

    base_label: str
    positive: Node
    negative: Node


def detect_contradictions(nodes: Iterable[Node]) -> Tuple[Contradiction, ...]:
    """
    Procura relações contraditórias (positivo vs negativo) no iterável *nodes*.

    A detecção é puramente estrutural: duas relações são contraditórias quando
    compartilham o mesmo label-base (ignorando prefixos/sufixos negativos) e a
    mesma assinatura de argumentos/campos, mas uma delas está marcada como
    negativa (`NOT_*`, `_NOT`, `!`, etc.).
    """

    positives: Dict[Signature, List[Node]] = {}
    negatives: Dict[Signature, List[Node]] = {}

    for node in nodes:
        if node.kind is not NodeKind.REL:
            continue
        label = node.label or ""
        base_label, polarity = _normalize_label(label)
        if not base_label:
            continue
        signature = _relation_signature(base_label, node)
        target = positives if polarity > 0 else negatives
        bucket = target.setdefault(signature, [])
        bucket.append(node)

    contradictions: List[Contradiction] = []
    shared_keys = set(positives.keys()) & set(negatives.keys())
    for key in shared_keys:
        base_label = key[0]
        for pos in positives[key]:
            for neg in negatives[key]:
                contradictions.append(Contradiction(base_label=base_label, positive=pos, negative=neg))
    return tuple(contradictions)


def _relation_signature(base_label: str, node: Node) -> Signature:
    args_sig = tuple(fingerprint(arg) for arg in node.args)
    fields_sig = tuple((key, fingerprint(value)) for key, value in node.fields)
    value_sig = repr(node.value) if node.value is not None else None
    return (base_label, args_sig, fields_sig, value_sig)


def _normalize_label(label: str) -> Tuple[str, int]:
    """
    Retorna `(label_base, polarity)` onde polarity ∈ {+1, -1}.

    Prefixos/sufixos negativos são removidos apenas do segmento final do label,
    preservando namespaces como `code/` ou `type::`.
    """

    if not label:
        return "", 1
    namespace, sep, leaf = _split_namespace(label.upper())
    core, is_negative = _strip_negation(leaf)
    if not core:
        core = leaf
    base = f"{namespace}{sep}{core}" if namespace else core
    return base, -1 if is_negative else 1


def _split_namespace(label: str) -> Tuple[str, str, str]:
    if "/" in label:
        namespace, _, leaf = label.rpartition("/")
        return namespace, "/", leaf
    if "::" in label:
        namespace, _, leaf = label.rpartition("::")
        return namespace, "::", leaf
    return "", "", label


def _strip_negation(token: str) -> Tuple[str, bool]:
    for prefix in _NEGATION_PREFIXES:
        if token.startswith(prefix) and len(token) > len(prefix):
            return token[len(prefix) :], True
    for suffix in _NEGATION_SUFFIXES:
        if token.endswith(suffix) and len(token) > len(suffix):
            return token[: -len(suffix)], True
    return token, False


__all__ = ["Contradiction", "detect_contradictions"]
