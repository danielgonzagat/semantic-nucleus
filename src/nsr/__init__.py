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
    EquationInvariantStatus,
)
from .state import SessionCtx, Config, Rule, Lexicon
from .lex import tokenize, compose_lexicon, load_lexicon_file
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
    "EquationInvariantStatus",
    "SessionCtx",
    "Config",
    "Rule",
    "Lexicon",
    "tokenize",
    "compose_lexicon",
    "load_lexicon_file",
    "build_struct",
]
