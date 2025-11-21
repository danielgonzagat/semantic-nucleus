"""Pacote NSR - Núcleo Semântico Reativo."""

from .runtime import run_text, run_struct, Trace
from .state import SessionCtx, Config, Rule, Lexicon
from .lex import tokenize
from .parser import build_struct

__all__ = [
    "run_text",
    "run_struct",
    "Trace",
    "SessionCtx",
    "Config",
    "Rule",
    "Lexicon",
    "tokenize",
    "build_struct",
]
