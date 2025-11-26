"""
Φ-INTENT v2 – Symbolic Pattern Matching DSL.

Replaces hardcoded keyword spotting with a structural pattern matcher
that binds variables using the Unification Engine.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any

from .core_unification import unify, Variable, var
from .semantic_mapper import SemanticParse # Keeping dependency for signature compatibility

@dataclass
class IntentFrame:
    label: str
    confidence: float
    variables: Dict[str, Any] = field(default_factory=dict)
    reasons: List[str] = field(default_factory=list)

@dataclass
class IntentPattern:
    intent_name: str
    template: List[Any] # List of strings or Variables
    score: float

class IntentMatcher:
    def __init__(self):
        self.patterns: List[IntentPattern] = []
        self._compile_defaults()

    def _compile_defaults(self):
        # Define variables
        x = var("target")
        
        # Definition Requests
        self.add("definition_request", ["define", x], 1.0)
        self.add("definition_request", ["o", "que", "e", x], 1.0)
        self.add("definition_request", ["what", "is", x], 1.0)
        self.add("definition_request", ["quem", "e", x], 1.0)
        
        # Arithmetic (simple trigger)
        self.add("calculate", ["calcule", x], 1.0)
        self.add("calculate", ["quanto", "e", x], 1.0)
        
        # Capabilities
        self.add("capability_query", ["o", "que", "voce", "faz"], 1.0)
        self.add("capability_query", ["quem", "e", "voce"], 1.0)

    def add(self, intent: str, template: List[Any], score: float):
        self.patterns.append(IntentPattern(intent, template, score))

    def match(self, tokens: List[str]) -> Optional[IntentFrame]:
        tokens_lower = [t.lower() for t in tokens]
        best_intent = None
        best_score = 0.0
        
        for pat in self.patterns:
            # Unify the template list with the token list
            # Note: This is simple list unification. 
            # For robust NLP, we'd need sequence alignment, but this is a huge step up from Regex.
            
            # If lengths differ significantly, skip (or handle partials later)
            if len(pat.template) != len(tokens_lower):
                continue
                
            subst = unify(pat.template, tokens_lower, {})
            
            if subst is not None:
                # Success!
                vars_clean = {k.name: v for k, v in subst.items()}
                return IntentFrame(
                    label=pat.intent_name,
                    confidence=pat.score,
                    variables=vars_clean,
                    reasons=[f"Matched pattern: {pat.template}"]
                )

        return None

# Global matcher
_MATCHER = IntentMatcher()

def phi_intent(parse: Any, idx: Any = None) -> IntentFrame:
    """
    Entry point compatible with old system.
    """
    # Extract text tokens
    if hasattr(parse, "tokens"):
        # semantic tokens have .lower attribute
        tokens = [t.lower for t in parse.tokens if not t.is_punctuation]
    else:
        # Fallback
        text = getattr(parse, "text", str(parse))
        tokens = text.lower().split()

    # 1. Try Structural Match
    result = _MATCHER.match(tokens)
    if result:
        return result

    # 2. Fallback Heuristics (for things not in DSL yet)
    if "?" in tokens or (hasattr(parse, "text") and "?" in parse.text):
        return IntentFrame("question", 0.5, reason=["Fallback: Question mark detected"])

    return IntentFrame("statement", 0.3, reason=["Default fallback"])