"""Rule-based semantic layer used by the PhiEngine."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Sequence

from .semantic_frames import FrameMatch


STOPWORDS = {
    "o",
    "a",
    "os",
    "as",
    "de",
    "do",
    "da",
    "um",
    "uma",
    "the",
    "and",
    "or",
}


@dataclass()
class UtteranceView:
    text: str
    lang: str
    tokens: List[str]
    lowered: str

    @classmethod
    def from_text(cls, text: str, lang: str, tokens: Sequence[str]) -> "UtteranceView":
        return cls(text=text, lang=lang, tokens=[tok for tok in tokens if tok], lowered=text.lower())


@dataclass()
class RuleMatch:
    rule_id: str
    intent: Optional[str]
    tags: Sequence[str]
    roles: Dict[str, str]
    confidence_delta: float


@dataclass()
class RuleAnalysis:
    intent: Optional[str]
    confidence: float
    tags: List[str]
    roles: Dict[str, str]
    fired_rules: List[str]


def _tokenize(text: str) -> List[str]:
    return [token.lower() for token in text.replace("?", " ? ").replace("!", " ! ").split()]


def build_view(text: str, lang: str, tokens: Optional[Sequence[str]] = None) -> UtteranceView:
    if tokens is None:
        tokens = _tokenize(text)
    return UtteranceView.from_text(text, lang, tokens)


def _apply_rules(utt: UtteranceView, frame: Optional[FrameMatch]) -> List[RuleMatch]:
    lowered = utt.lowered
    tokens = utt.tokens
    matches: List[RuleMatch] = []

    def add(rule_id: str, intent: Optional[str], tags: Sequence[str], roles: Optional[Dict[str, str]] = None, boost: float = 0.2) -> None:
        matches.append(
            RuleMatch(
                rule_id=rule_id,
                intent=intent,
                tags=tuple(tags),
                roles=roles or {},
                confidence_delta=boost,
            )
        )

    # Greeting
    greetings = {"oi", "olá", "ola", "hello", "hi", "hey", "bom dia", "boa tarde", "boa noite"}
    if any(token in greetings for token in tokens):
        add("rule_greeting", "social_greeting", ("social", "opening"), boost=0.5)

    # Thanks
    thanks_tokens = {"obrigado", "obrigada", "valeu", "thanks", "thank", "appreciate"}
    if any(token in thanks_tokens for token in tokens):
        add("rule_thanks", "social_thanks", ("social",), boost=0.4)

    # Apology
    apology_tokens = {"desculpa", "perdão", "foi", "mal", "sorry", "apologize"}
    if "sorry" in lowered or any(token in apology_tokens for token in tokens):
        add("rule_apology", "social_apology", ("social",), boost=0.4)

    # Question mark heuristic
    if lowered.strip().endswith("?"):
        add("rule_question_mark", "question_generic", ("question",), boost=0.35)

    # Why / porque
    if "por que" in lowered or "porque" in lowered or "why" in lowered:
        add("rule_causal_question", "ask_cause", ("question", "causal"), boost=0.45)

    # Definition question
    if "o que é" in lowered or "o que e" in lowered or "what is" in lowered:
        add("rule_definition_question", "ask_definition", ("question", "definition"), boost=0.45)

    # Who question
    if "quem é" in lowered or "who is" in lowered:
        add("rule_identity_question", "ask_identity", ("question", "identity"), boost=0.4)

    # How question
    if "como " in lowered or "how " in lowered:
        add("rule_how_question", "ask_how", ("question", "procedural"), boost=0.35)

    # Meta reasoning
    if "passo a passo" in lowered or "raciocínio" in lowered or "reasoning" in lowered:
        add("rule_meta_reasoning", "meta_reasoning", ("meta",), boost=0.4)

    # Imperative detection (rudimentary)
    imperative_tokens = {"faça", "faca", "cria", "gera", "implementa", "execute", "run", "create", "generate", "explain"}
    if tokens:
        first = tokens[0]
        if first in imperative_tokens:
            intent = "command"
            if first in {"explain"} or "explica" in lowered:
                intent = "command_explain"
            add("rule_imperative", intent, ("command",), boost=0.4)

    # Use frame hint if available
    if frame and frame.intent:
        add("rule_frame_hint", frame.intent, tuple(frame.tags), roles=frame.frame.roles, boost=0.35)

    return matches


def apply_semantic_rules(utt: UtteranceView, frame: Optional[FrameMatch]) -> RuleAnalysis:
    matches = _apply_rules(utt, frame)
    if not matches:
        return RuleAnalysis(intent=None, confidence=0.0, tags=[], roles={}, fired_rules=[])

    # Aggregate intent votes
    intent_scores: Dict[str, float] = {}
    tags: List[str] = []
    roles: Dict[str, str] = {}
    fired_rules: List[str] = []

    for match in matches:
        fired_rules.append(match.rule_id)
        tags.extend(tag for tag in match.tags if tag not in tags)
        roles.update(match.roles)
        if not match.intent:
            continue
        intent_scores[match.intent] = intent_scores.get(match.intent, 0.0) + match.confidence_delta

    if not intent_scores:
        best_intent = None
        confidence = 0.0
    else:
        best_intent = max(intent_scores.items(), key=lambda item: item[1])[0]
        confidence = min(0.95, intent_scores[best_intent])

    return RuleAnalysis(
        intent=best_intent,
        confidence=confidence,
        tags=tags,
        roles=roles,
        fired_rules=fired_rules,
    )
