"""
OpCodes oficiais suportados pela ΣVM de referência.
"""

from __future__ import annotations

from enum import IntEnum


class Opcode(IntEnum):
    PUSH_TEXT = 0x01
    BUILD_STRUCT = 0x02
    STORE_ANSWER = 0x03
    HALT = 0xFF


__all__ = ["Opcode"]
