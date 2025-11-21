"""
Deterministic structural fingerprints for LIU nodes.
"""

from __future__ import annotations

from hashlib import blake2b

from .nodes import Node


def _flatten(node: Node) -> str:
    parts: list[str] = [node.kind.value]
    if node.label is not None:
        parts.append(f"L={node.label}")
    if node.value is not None:
        parts.append(f"V={node.value!r}")
    if node.fields:
        field_repr = []
        for key, value in node.fields:
            field_repr.append(f"{key}:{_flatten(value)}")
        parts.append(f"F[{';'.join(field_repr)}]")
    if node.args:
        arg_repr = ",".join(_flatten(arg) for arg in node.args)
        parts.append(f"A[{arg_repr}]")
    return "|".join(parts)


def fingerprint(node: Node) -> str:
    """
    Compute a 128-bit Blake2b fingerprint of *node*.

    The fingerprint is stable across processes for structurally identical nodes,
    provided the node is already canonical (use ``liu.normalize`` beforehand
    when comparing arbitrary nodes).
    """

    payload = _flatten(node)
    return blake2b(payload.encode("utf-8"), digest_size=16).hexdigest()


__all__ = ["fingerprint"]
