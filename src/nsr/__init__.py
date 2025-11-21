"""Pacote NSR - Núcleo Semântico Reativo."""

from .runtime import (
    run_text,
    run_struct,
    run_text_full,
    run_struct_full,
    Trace,
    HaltReason,
    RunOutcome,
    EquationSnapshot,
    EquationSnapshotStats,
)
from .state import SessionCtx, Config, Rule, Lexicon
from .lex import tokenize
from .parser import build_struct

__all__ = [
    "run_text",
    "run_struct",
    "Trace",
    "run_text_full",
    "run_struct_full",
    "HaltReason",
    "RunOutcome",
    "EquationSnapshot",
    "EquationSnapshotStats",
    "SessionCtx",
    "Config",
    "Rule",
    "Lexicon",
    "tokenize",
    "build_struct",
]
