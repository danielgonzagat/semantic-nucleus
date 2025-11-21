"""
OpCodes oficiais suportados pela ΣVM de referência.
"""

from __future__ import annotations

from enum import IntEnum


class Opcode(IntEnum):
    PUSH_TEXT = 0x01
    PUSH_CONST = 0x02
    PUSH_KEY = 0x03
    BUILD_STRUCT = 0x04
    BEGIN_STRUCT = 0x05
    NOOP = 0x10
    LOAD_REG = 0x11
    STORE_REG = 0x12
    STORE_ANSWER = 0x80
    HALT = 0xFF


__all__ = ["Opcode"]
