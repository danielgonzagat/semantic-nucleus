"""Meta-linguistic scoring utilities."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, List, Optional, Sequence, Set

from .semantic_mapper import SemanticParse
from .semantic_frames import FrameMatch
from .semantic_rules import RuleAnalysis


LOGICAL_MARKERS = {
    "se",
    "então",
    "logo",
    "portanto",
    "porque",
    "por",
    "que",
    "if",
    "then",
    "therefore",
    "thus",
    "because",
    "and",
    "or",
    "but",
}


@dataclass()
class SemanticMetrics:
    surprise: float
    redundancy: float
    coherence: float
    conceptual_distance: float
    logical_density: float
    signals: List[str] = field(default_factory=list)


def _clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    if value < lo:
        return lo
    if value > hi:
        return hi
    return value


def _logical_density(tokens: Sequence[str]) -> float:
    if not tokens:
        return 0.0
    count = sum(1 for token in tokens if token in LOGICAL_MARKERS)
    return _clamp(count / max(1, len(tokens) * 0.5))


def _redundancy(tokens: Sequence[str]) -> float:
    if not tokens:
        return 0.0
    unique = len(set(tokens))
    return _clamp(1.0 - unique / len(tokens))


def _surprise(concept_hits: int, token_count: int) -> float:
    if token_count == 0:
        return 0.0
    ratio = concept_hits / token_count
    return _clamp(1.0 - ratio * 0.8)


def _conceptual_distance(categories: Set[str]) -> float:
    if not categories:
        return 0.2
    return _clamp(len(categories) / 6.0)


def compute_semantic_metrics(
    parse: SemanticParse,
    best_frame: Optional[FrameMatch],
    rule_analysis: RuleAnalysis,
    recent_concepts: Iterable[str],
    dominant_concepts: Iterable[str],
) -> SemanticMetrics:
    tokens = [token.lower for token in parse.tokens if not token.is_punctuation]
    signals: List[str] = []

    concept_hits = len({hit.token.lower for hit in parse.hits})
    token_count = len(tokens)
    signals.append(f"tokens={token_count}")
    signals.append(f"concept_hits={concept_hits}")

    surprise = _surprise(concept_hits, token_count)
    redundancy = _redundancy(tokens)
    logical_density = _logical_density(tokens)

    coherence = 0.2
    if best_frame:
        coherence += 0.3
        signals.append(f"frame={best_frame.id}")
    if rule_analysis.intent:
        coherence += 0.3
        signals.append(f"rule_intent={rule_analysis.intent}")
    if rule_analysis.tags:
        coherence += min(0.2, len(rule_analysis.tags) * 0.05)
    coherence = _clamp(coherence)

    categories = {hit.category_id[:4] for hit in parse.hits}
    conceptual_distance = _conceptual_distance(categories)

    recent = set(recent_concepts)
    dominant = set(dominant_concepts)
    if recent:
        overlap = len(recent & {hit.token.lower for hit in parse.hits})
        coherence += _clamp(overlap / max(1, len(recent))) * 0.2
    if dominant:
        overlap = len(dominant & {hit.token.lower for hit in parse.hits})
        surprise -= _clamp(overlap / max(1, len(dominant))) * 0.2

    return SemanticMetrics(
        surprise=_clamp(surprise),
        redundancy=_clamp(redundancy),
        coherence=_clamp(coherence),
        conceptual_distance=_clamp(conceptual_distance),
        logical_density=_clamp(logical_density),
        signals=signals,
    )
