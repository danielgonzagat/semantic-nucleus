"""
OpCodes oficiais suportados pela ΣVM de referência.

A ISA agora cobre construção completa de nós LIU, operações sobre o estado ISR
interno e instruções de controle/diagnóstico para auditoria determinística.
"""

from __future__ import annotations

from enum import IntEnum


class Opcode(IntEnum):
    # Pilha / constantes
    PUSH_TEXT = 0x01
    PUSH_CONST = 0x02
    PUSH_KEY = 0x03
    PUSH_NUMBER = 0x04
    PUSH_BOOL = 0x05

    # Registradores
    LOAD_REG = 0x10
    STORE_REG = 0x11

    # Construção de nós LIU
    NEW_STRUCT = 0x20
    BUILD_STRUCT = NEW_STRUCT  # compat
    BEGIN_STRUCT = NEW_STRUCT  # compat
    NEW_LIST = 0x21
    NEW_REL = 0x22
    NEW_OP = 0x23
    GET_FIELD = 0x24
    SET_FIELD = 0x25

    # Manipulação de estado ISR
    ADD_REL = 0x30
    HAS_REL = 0x31
    UNIFY_EQ = 0x40
    UNIFY_REL = 0x41
    ENQ_OP = 0x50
    DISPATCH = 0x51

    # Atalhos Φ (operações NSR)
    PHI_NORMALIZE = 0x60
    PHI_INFER = 0x61
    PHI_ANSWER = 0x62
    PHI_EXPLAIN = 0x63
    PHI_SUMMARIZE = 0x64
    PHI_MEMORY_RECALL = 0x65
    PHI_MEMORY_LINK = 0x66

    # Controle de fluxo / auditoria
    JMP = 0x70
    CALL = 0x71
    RET = 0x72
    HASH_STATE = 0x80

    # Saída e fluxo
    STORE_ANSWER = 0x90
    NOOP = 0xF0
    TRAP = 0xFE
    HALT = 0xFF


__all__ = ["Opcode"]
