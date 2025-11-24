"""ΣVM reference tools."""

from .vm import SigmaVM, Program, build_program_from_assembly
from .assembler import assemble, disassemble
from .bytecode import encode, decode
from .opcodes import Opcode
from .verifier import verify_program, VerificationError
from .snapshots import (
    SNAPSHOT_VERSION,
    SnapshotSignature,
    SVMSnapshot,
    build_snapshot,
    save_snapshot,
    load_snapshot,
    restore_snapshot,
)
from .signing import (
    Ed25519Unavailable,
    generate_ed25519_keypair,
    sign_snapshot,
    verify_snapshot_signature,
)

__all__ = [
    "SigmaVM",
    "Program",
    "build_program_from_assembly",
    "assemble",
    "disassemble",
    "encode",
    "decode",
    "Opcode",
    "verify_program",
    "VerificationError",
    "SNAPSHOT_VERSION",
    "SnapshotSignature",
    "SVMSnapshot",
    "build_snapshot",
    "save_snapshot",
    "load_snapshot",
    "restore_snapshot",
    "Ed25519Unavailable",
    "generate_ed25519_keypair",
    "sign_snapshot",
    "verify_snapshot_signature",
]
