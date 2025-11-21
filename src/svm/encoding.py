"""
Funções utilitárias de varint para bytecode ΣVM.
"""

from __future__ import annotations


def encode_varint(value: int) -> bytes:
    out = bytearray()
    v = value
    while True:
        byte = v & 0x7F
        v >>= 7
        if v:
            out.append(0x80 | byte)
        else:
            out.append(byte)
            break
    return bytes(out)


def decode_varint(data: bytes, offset: int = 0) -> tuple[int, int]:
    shift = 0
    result = 0
    pos = offset
    while True:
        if pos >= len(data):
            raise ValueError("unterminated varint")
        byte = data[pos]
        pos += 1
        result |= (byte & 0x7F) << shift
        if not byte & 0x80:
            break
        shift += 7
    return result, pos


__all__ = ["encode_varint", "decode_varint"]
