"""
Utilities for persisting ΣVM state into deterministic snapshot bundles.
"""

from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from hashlib import blake2b
from pathlib import Path
from typing import Any, Dict, Iterable, Sequence

from liu import Node
from liu.serialize import to_json
from nsr.state import ISR

from .bytecode import encode
from .vm import SigmaVM

try:  # pragma: no cover - optional acceleration
    import blake3 as _blake3
except Exception:  # pragma: no cover - fallback uses stdlib
    _blake3 = None

SNAPSHOT_VERSION = "svms/1"


def _hash_bytes(payload: bytes) -> str:
    if _blake3 is not None:
        return _blake3.blake3(payload).hexdigest()
    return blake2b(payload, digest_size=32).hexdigest()


def _node_payload(node: Node) -> Dict[str, Any]:
    return json.loads(to_json(node))


def _nodes_payload(nodes: Iterable[Node]) -> list[Dict[str, Any]]:
    return [_node_payload(node) for node in nodes]


def _serialize_constant(value: Any) -> Any:
    if isinstance(value, Node):
        return {"type": "node", "value": _node_payload(value)}
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, (list, tuple)):
        return [_serialize_constant(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _serialize_constant(item) for key, item in value.items()}
    return {"type": "repr", "value": repr(value)}


def _serialize_isr(isr: ISR | None) -> Dict[str, Any] | None:
    if isr is None:
        return None
    return {
        "ontology": _nodes_payload(isr.ontology),
        "relations": _nodes_payload(isr.relations),
        "context": _nodes_payload(isr.context),
        "goals": _nodes_payload(tuple(isr.goals)),
        "ops_queue": _nodes_payload(tuple(isr.ops_queue)),
        "answer": _node_payload(isr.answer),
        "quality": isr.quality,
    }


def _vm_state_payload(vm: SigmaVM) -> Dict[str, Any]:
    raw = vm.snapshot()
    answer_node = raw.get("answer")
    return {
        "pc": raw["pc"],
        "stack_depth": raw["stack_depth"],
        "registers": raw["registers"],
        "isr_digest": raw["isr_digest"],
        "answer": _node_payload(answer_node) if answer_node else None,
    }


@dataclass(slots=True)
class SVMSnapshot:
    """
    Materialized representation of a ΣVM snapshot bundle.
    """

    version: str
    digest: str
    bytecode_b64: str
    constants: Sequence[Any]
    isr: Dict[str, Any] | None
    vm_state: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version": self.version,
            "digest": self.digest,
            "program": {
                "bytecode": self.bytecode_b64,
                "constants": self.constants,
            },
            "state": {
                "isr": self.isr,
                "vm": self.vm_state,
            },
        }

    def dumps(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, separators=(",", ":"))

    def save(self, path: str | Path) -> Path:
        target = Path(path)
        target.write_text(self.dumps() + "\n", encoding="utf-8")
        return target


def build_snapshot(vm: SigmaVM) -> SVMSnapshot:
    """
    Capture the current ΣVM state (program + ISR) into a deterministic bundle.
    """

    if vm.program is None:
        raise RuntimeError("SigmaVM program must be loaded before snapshotting")
    program_bytes = encode(vm.program.instructions)
    bytecode_b64 = base64.b64encode(program_bytes).decode("ascii")
    constants_payload = [_serialize_constant(value) for value in vm.program.constants]
    isr_payload = _serialize_isr(vm.isr)
    vm_payload = _vm_state_payload(vm)
    payload = {
        "version": SNAPSHOT_VERSION,
        "program": {
            "bytecode": bytecode_b64,
            "constants": constants_payload,
        },
        "state": {
            "isr": isr_payload,
            "vm": vm_payload,
        },
    }
    digest = _hash_bytes(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8"))
    return SVMSnapshot(
        version=SNAPSHOT_VERSION,
        digest=digest,
        bytecode_b64=bytecode_b64,
        constants=constants_payload,
        isr=isr_payload,
        vm_state=vm_payload,
    )


def save_snapshot(vm: SigmaVM, path: str | Path) -> SVMSnapshot:
    """
    Persist the ΣVM snapshot to disk (.svms by convention) and return it.
    """

    snapshot = build_snapshot(vm)
    snapshot.save(path)
    return snapshot


def load_snapshot(path: str | Path) -> Dict[str, Any]:
    """
    Load a snapshot bundle from disk as a raw dictionary.
    """

    content = Path(path).read_text(encoding="utf-8")
    return json.loads(content)


__all__ = ["SVMSnapshot", "SNAPSHOT_VERSION", "build_snapshot", "save_snapshot", "load_snapshot"]
