"""
Digital signatures for ΣVM snapshot bundles.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass
from typing import Tuple

from .snapshots import SVMSnapshot, SnapshotSignature

try:  # pragma: no cover - optional dependency
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import (
        Ed25519PrivateKey,
        Ed25519PublicKey,
    )
except Exception:  # pragma: no cover - fallback handled via guard
    Ed25519PrivateKey = None
    Ed25519PublicKey = None


class Ed25519Unavailable(RuntimeError):
    pass


def _ensure_ed25519() -> None:
    if Ed25519PrivateKey is None or Ed25519PublicKey is None:
        raise Ed25519Unavailable(
            "cryptography.ed25519 not available; install `cryptography>=43` to enable signing"
        )


def _b64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def _b64decode(data: str) -> bytes:
    return base64.b64decode(data.encode("ascii"))


def generate_ed25519_keypair() -> Tuple[str, str]:
    """
    Generate a deterministic Ed25519 keypair encoded in base64 (public, private).
    """

    _ensure_ed25519()
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()
    public_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    private_bytes = private_key.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption(),
    )
    return _b64(public_bytes), _b64(private_bytes)


def sign_snapshot(snapshot: SVMSnapshot, private_key_b64: str) -> SnapshotSignature:
    """
    Produce an Ed25519 signature over the canonical snapshot payload.
    """

    _ensure_ed25519()
    private_key = Ed25519PrivateKey.from_private_bytes(_b64decode(private_key_b64))
    signature = private_key.sign(snapshot.canonical_bytes())
    public_key = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return SnapshotSignature(
        algorithm="ed25519",
        public_key=_b64(public_key),
        signature=_b64(signature),
    )


def verify_snapshot_signature(snapshot: SVMSnapshot, signature: SnapshotSignature) -> bool:
    """
    Validate that a signature matches the provided snapshot.
    """

    if signature.algorithm.lower() != "ed25519":
        raise ValueError(f"Unsupported signature algorithm {signature.algorithm}")
    _ensure_ed25519()
    public_key = Ed25519PublicKey.from_public_bytes(_b64decode(signature.public_key))
    try:
        public_key.verify(_b64decode(signature.signature), snapshot.canonical_bytes())
        return True
    except Exception:  # pragma: no cover - rely on cryptography's verification
        return False


__all__ = [
    "SnapshotSignature",
    "Ed25519Unavailable",
    "generate_ed25519_keypair",
    "sign_snapshot",
    "verify_snapshot_signature",
]
