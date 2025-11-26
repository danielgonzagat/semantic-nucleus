"""
Serialização de bytecode SVMB.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple

from .encoding import encode_varint, decode_varint
from .opcodes import Opcode

MAGIC = b"SVMB"
VERSION = (1, 0)


@dataclass()
class Instruction:
    opcode: Opcode
    operand: int = 0


def encode(instructions: List[Instruction]) -> bytes:
    body = bytearray()
    for inst in instructions:
        body.append(inst.opcode)
        body.extend(encode_varint(inst.operand))
    header = bytearray()
    header.extend(MAGIC)
    header.extend(encode_varint(VERSION[0]))
    header.extend(encode_varint(VERSION[1]))
    header.extend(encode_varint(len(body)))
    return bytes(header + body)


def decode(blob: bytes) -> List[Instruction]:
    if not blob.startswith(MAGIC):
        raise ValueError("invalid magic")
    idx = len(MAGIC)
    _, idx = decode_varint(blob, idx)  # major
    _, idx = decode_varint(blob, idx)  # minor
    body_len, idx = decode_varint(blob, idx)
    body = blob[idx : idx + body_len]
    instructions: List[Instruction] = []
    pos = 0
    while pos < len(body):
        opcode = Opcode(body[pos])
        pos += 1
        operand, pos = decode_varint(body, pos)
        instructions.append(Instruction(opcode=opcode, operand=operand))
    return instructions


__all__ = ["Instruction", "encode", "decode", "MAGIC", "VERSION"]
