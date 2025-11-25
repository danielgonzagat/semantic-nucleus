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
from .polynomial_bridge import PolynomialHook, maybe_route_polynomial
from .polynomial_engine import PolynomialResult, factor_polynomial
from .logic_engine import LogicEngine, LogicRule, negate as logic_negate, normalize_statement as logic_normalize
from .logic_bridge import LogicBridgeResult, LogicHook, maybe_route_logic as logic_route, interpret_logic_command
from .bayes_bridge import BayesHook, maybe_route_bayes
from .bayes_engine import BayesNetwork, BayesVariable
from .markov_bridge import MarkovHook, maybe_route_markov
from .markov_engine import MarkovModel
from .factor_bridge import FactorHook, maybe_route_factor
from .factor_graph_engine import FactorGraph, FactorVariable, Factor
from .meta_transformer import MetaTransformer, MetaTransformResult, MetaRoute, meta_summary_to_dict, MetaCalculationPlan
from .meta_calculator import MetaCalculationResult, execute_meta_plan
from .meta_structures import (
    build_lc_meta_struct,
    lc_term_to_node,
    meta_calculation_to_node,
)
from .meta_expressor import build_meta_expression
from .meta_memory import build_meta_memory, meta_memory_to_dict
from .meta_reflection import build_meta_reflection
from .meta_synthesis import build_meta_synthesis
from .language_detector import detect_language_profile
from .code_ast import build_python_ast_meta, build_rust_ast_meta
from .math_ast import build_math_ast_node

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
    "PolynomialHook",
    "PolynomialResult",
    "factor_polynomial",
    "analyze_utterance",
    "plan_reply",
    "respond",
    "ian_encode_word",
    "ian_decode_codes",
    "ian_word_signature",
    "ian_conjugate",
    "maybe_route_text",
    "maybe_route_math",
    "maybe_route_polynomial",
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
    "BayesHook",
    "BayesNetwork",
    "BayesVariable",
    "maybe_route_bayes",
    "MarkovHook",
    "MarkovModel",
    "maybe_route_markov",
    "FactorHook",
    "FactorGraph",
    "FactorVariable",
    "Factor",
    "maybe_route_factor",
    "MetaTransformer",
    "MetaTransformResult",
    "MetaRoute",
    "MetaCalculationPlan",
    "MetaCalculationResult",
    "execute_meta_plan",
    "meta_summary_to_dict",
    "build_lc_meta_struct",
    "lc_term_to_node",
    "meta_calculation_to_node",
    "detect_language_profile",
    "build_python_ast_meta",
    "build_math_ast_node",
    "build_rust_ast_meta",
    "build_meta_expression",
    "build_meta_memory",
    "meta_memory_to_dict",
    "build_meta_synthesis",
    "build_meta_reflection",
]
