from __future__ import annotations

from typing import Iterable, List, Tuple

from nsr_evo.kb_store import RuleSpec


def filter_novel_rules(
    proposed: Iterable[RuleSpec],
    existing: Iterable[RuleSpec],
) -> list[RuleSpec]:
    existing_keys = {
        (_norm_patterns(rule.if_all), _norm_patterns([rule.then])[0])
        for rule in existing
    }
    accepted: List[RuleSpec] = []
    for spec in proposed:
        key = (_norm_patterns(spec.if_all), _norm_patterns([spec.then])[0])
        if key in existing_keys:
            continue
        accepted.append(spec)
    return accepted


def sort_by_energy(specs: Iterable[RuleSpec]) -> list[RuleSpec]:
    return sorted(specs, key=lambda spec: -int(getattr(spec, "support", 1)))


def _norm_patterns(patterns: Iterable[dict]) -> Tuple[Tuple[str, Tuple[str, ...]], ...]:
    normalized = []
    for pattern in patterns:
        rel = str(pattern.get("rel") or pattern.get("label") or "")
        args = tuple(str(arg) for arg in pattern.get("args", []))
        normalized.append((rel, args))
    return tuple(sorted(normalized))
