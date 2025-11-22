"""Pacote NSR - Núcleo Semântico Reativo."""

from .runtime import (
    run_text,
    run_text_with_explanation,
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
from .explain import render_explanation, render_struct_sentence, render_struct_node
from .ian import (
    IANInstinct,
    analyze_utterance,
    plan_reply,
    respond,
    encode_word as ian_encode_word,
    decode_codes as ian_decode_codes,
    word_signature as ian_word_signature,
    conjugate as ian_conjugate,
)
from .ian_bridge import (
    InstinctHook,
    maybe_route_text,
    utterance_to_struct,
    reply_plan_to_answer,
)
from .code_bridge import CodeHook, maybe_route_code
from .math_instinct import MathInstinct
from .math_bridge import maybe_route_math
from .logic_engine import LogicEngine, LogicRule, negate as logic_negate, normalize_statement as logic_normalize
from .logic_bridge import LogicBridgeResult, LogicHook, maybe_route_logic as logic_route, interpret_logic_command
from .meta_transformer import MetaTransformer, MetaTransformResult, MetaRoute, meta_summary_to_dict, MetaCalculationPlan

__all__ = [
    "run_text",
    "run_struct",
    "Trace",
    "run_text_with_explanation",
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
    "render_explanation",
    "render_struct_sentence",
    "render_struct_node",
    "IANInstinct",
    "InstinctHook",
    "CodeHook",
    "MathInstinct",
    "analyze_utterance",
    "plan_reply",
    "respond",
    "ian_encode_word",
    "ian_decode_codes",
    "ian_word_signature",
    "ian_conjugate",
    "maybe_route_text",
    "maybe_route_math",
    "utterance_to_struct",
    "reply_plan_to_answer",
    "maybe_route_code",
    "LogicEngine",
    "LogicRule",
    "LogicHook",
    "logic_negate",
    "logic_normalize",
    "LogicBridgeResult",
    "logic_route",
    "interpret_logic_command",
    "MetaTransformer",
    "MetaTransformResult",
    "MetaRoute",
    "MetaCalculationPlan",
    "meta_summary_to_dict",
]
