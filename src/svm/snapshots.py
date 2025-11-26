"""
Utilities for persisting ΣVM state into deterministic snapshot bundles.
"""

from __future__ import annotations

import base64
import json
from collections import deque
from dataclasses import dataclass, replace
from hashlib import blake2b
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence, Tuple

from liu import Node, struct
from liu.serialize import to_json, from_json
from nsr.state import ISR, SessionCtx

from .bytecode import encode, decode
from .vm import SigmaVM, Program

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


def _deserialize_constant(value: Any) -> Any:
    if isinstance(value, dict):
        marker = value.get("type")
        if marker == "node":
            return _node_from_payload(value["value"])
        if marker == "repr":
            return value.get("value")
        return {key: _deserialize_constant(val) for key, val in value.items()}
    if isinstance(value, list):
        return [_deserialize_constant(item) for item in value]
    return value


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


def _node_from_payload(payload: Dict[str, Any]) -> Node:
    return from_json(json.dumps(payload))


def _nodes_from_payload(payload: Iterable[Dict[str, Any]]) -> Tuple[Node, ...]:
    return tuple(_node_from_payload(item) for item in payload)


def _isr_from_payload(payload: Dict[str, Any] | None, session: SessionCtx) -> ISR | None:
    if payload is None:
        return None
    ontology = _nodes_from_payload(payload.get("ontology", ()))
    relations = _nodes_from_payload(payload.get("relations", ()))
    context = _nodes_from_payload(payload.get("context", ()))
    goals = deque(_nodes_from_payload(payload.get("goals", ())))
    ops_queue = deque(_nodes_from_payload(payload.get("ops_queue", ())))
    answer_payload = payload.get("answer")
    answer = _node_from_payload(answer_payload) if answer_payload else struct()
    quality = float(payload.get("quality", 0.0))
    return ISR(
        ontology=ontology,
        relations=relations,
        context=context,
        goals=goals,
        ops_queue=ops_queue,
        answer=answer,
        quality=quality,
    )


def _vm_state_payload(vm: SigmaVM) -> Dict[str, Any]:
    raw = vm.snapshot()
    answer_node = raw.get("answer")
    return {
        "pc": raw["pc"],
        "stack_depth": raw["stack_depth"],
        "stack": [_node_payload(node) for node in raw.get("stack", [])],
        "registers": raw["registers"],
        "register_values": [
            _node_payload(node) if node else None for node in raw.get("register_values", [])
        ],
        "call_stack": list(raw.get("call_stack", [])),
        "isr_digest": raw["isr_digest"],
        "answer": _node_payload(answer_node) if answer_node else None,
    }


def _vm_state_from_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    registers = payload.get("register_values", [])
    stack_payload = payload.get("stack", [])
    return {
        "pc": int(payload.get("pc", 0)),
        "stack": [_node_from_payload(item) for item in stack_payload],
        "register_values": [
            _node_from_payload(item) if item else None for item in registers
        ],
        "call_stack": list(payload.get("call_stack", [])),
        "answer": _node_from_payload(payload["answer"]) if payload.get("answer") else None,
    }


def _body_dict(
    version: str,
    bytecode_b64: str,
    constants_payload: Sequence[Any],
    isr_payload: Dict[str, Any] | None,
    vm_payload: Dict[str, Any],
) -> Dict[str, Any]:
    return {
        "version": version,
        "program": {
            "bytecode": bytecode_b64,
            "constants": constants_payload,
        },
        "state": {
            "isr": isr_payload,
            "vm": vm_payload,
        },
    }


def _canonical_bytes(body: Dict[str, Any]) -> bytes:
    return json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")


@dataclass()
class SnapshotSignature:
    algorithm: str
    public_key: str
    signature: str

    def to_dict(self) -> Dict[str, str]:
        return {
            "algorithm": self.algorithm,
            "public_key": self.public_key,
            "signature": self.signature,
        }

    @staticmethod
    def from_dict(payload: Dict[str, str]) -> "SnapshotSignature":
        return SnapshotSignature(
            algorithm=payload["algorithm"],
            public_key=payload["public_key"],
            signature=payload["signature"],
        )


@dataclass()
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
    signatures: Tuple[SnapshotSignature, ...] = ()

    def to_dict(self) -> Dict[str, Any]:
        body = _body_dict(self.version, self.bytecode_b64, self.constants, self.isr, self.vm_state)
        payload = {"digest": self.digest, **body}
        if self.signatures:
            payload["signatures"] = [sig.to_dict() for sig in self.signatures]
        return payload

    def dumps(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, separators=(",", ":"))

    def save(self, path: str | Path) -> Path:
        target = Path(path)
        target.write_text(self.dumps() + "\n", encoding="utf-8")
        return target

    def with_signature(self, signature: SnapshotSignature) -> "SVMSnapshot":
        return replace(self, signatures=tuple((*self.signatures, signature)))

    def canonical_bytes(self) -> bytes:
        return _canonical_bytes(_body_dict(self.version, self.bytecode_b64, self.constants, self.isr, self.vm_state))


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
    body = _body_dict(SNAPSHOT_VERSION, bytecode_b64, constants_payload, isr_payload, vm_payload)
    digest = _hash_bytes(_canonical_bytes(body))
    return SVMSnapshot(
        version=SNAPSHOT_VERSION,
        digest=digest,
        bytecode_b64=bytecode_b64,
        constants=constants_payload,
        isr=isr_payload,
        vm_state=vm_payload,
        signatures=(),
    )


def save_snapshot(vm: SigmaVM, path: str | Path) -> SVMSnapshot:
    """
    Persist the ΣVM snapshot to disk (.svms by convention) and return it.
    """

    snapshot = build_snapshot(vm)
    snapshot.save(path)
    return snapshot


def _snapshot_from_dict(payload: Dict[str, Any]) -> SVMSnapshot:
    program = payload["program"]
    state = payload["state"]
    signatures_payload = payload.get("signatures", ())
    snapshot = SVMSnapshot(
        version=payload["version"],
        digest=payload["digest"],
        bytecode_b64=program["bytecode"],
        constants=program["constants"],
        isr=state.get("isr"),
        vm_state=state["vm"],
        signatures=tuple(SnapshotSignature.from_dict(item) for item in signatures_payload),
    )
    expected = _hash_bytes(snapshot.canonical_bytes())
    if expected != snapshot.digest:
        raise ValueError("snapshot digest mismatch")
    return snapshot


def load_snapshot(path: str | Path) -> SVMSnapshot:
    """
    Load a snapshot bundle from disk e validá-lo.
    """

    content = Path(path).read_text(encoding="utf-8")
    return _snapshot_from_dict(json.loads(content))


def restore_snapshot(snapshot: SVMSnapshot, session: SessionCtx | None = None) -> SigmaVM:
    """
    Recreate a SigmaVM from a snapshot (program + ISR + registradores/pilha).
    """

    program_bytes = base64.b64decode(snapshot.bytecode_b64.encode("ascii"))
    instructions = decode(program_bytes)
    constants = [_deserialize_constant(value) for value in snapshot.constants]
    program = Program(instructions=instructions, constants=constants)
    vm = SigmaVM(session=session)
    restored_isr = _isr_from_payload(snapshot.isr, vm.session)
    vm.load(program, session=vm.session, isr_state=restored_isr)
    vm_state = _vm_state_from_payload(snapshot.vm_state)
    vm.pc = vm_state["pc"]
    vm.stack = vm_state["stack"]
    register_values = vm_state["register_values"]
    for idx in range(min(len(register_values), len(vm.registers))):
        vm.registers[idx] = register_values[idx]
    vm.call_stack = list(vm_state["call_stack"])
    vm.answer = vm_state["answer"]
    return vm


__all__ = [
    "SVMSnapshot",
    "SnapshotSignature",
    "SNAPSHOT_VERSION",
    "build_snapshot",
    "save_snapshot",
    "load_snapshot",
    "restore_snapshot",
]
