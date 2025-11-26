from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Dict, Iterable, List, Tuple

from nsr import RunOutcome
from nsr_evo.kb_store import RuleSpec


@dataclass()
class InductionConfig:
    min_quality: float = 0.6
    max_contradictions: int = 0
    min_support: int = 3
    max_new_rules_per_cycle: int = 8


@dataclass()
class EpisodeView:
    text: str
    outcome: RunOutcome


def _extract_relations_from_equation(outcome: RunOutcome) -> list[dict]:
    bundle = outcome.equation.to_json_bundle()
    rels = []
    for node in bundle.get("relations", []):
        label = node.get("label") or ""
        if node.get("kind") != "REL" or not label:
            continue
        args = []
        for arg in node.get("args", []):
            if isinstance(arg, dict) and arg.get("label"):
                args.append(arg["label"])
            elif isinstance(arg, dict) and arg.get("value") is not None:
                args.append(str(arg["value"]))
            else:
                args.append(repr(arg))
        rels.append({"rel": label, "args": args})
    return rels


def _triples_from_relations(rels: Iterable[dict]) -> list[Tuple[str, str, str]]:
    triples: list[Tuple[str, str, str]] = []
    for rel in rels:
        label = rel.get("rel") or ""
        args = rel.get("args") or []
        if len(args) >= 2:
            triples.append((label, str(args[0]), str(args[1])))
    return triples


def induce_rules(
    episodes: Iterable[EpisodeView],
    cfg: InductionConfig,
) -> list[RuleSpec]:
    cooc_counter: Dict[Tuple[Tuple[str, str, str], Tuple[str, str, str]], int] = Counter()

    for episode in episodes:
        outcome = episode.outcome
        if outcome.quality < cfg.min_quality:
            continue
        contradictions = len(getattr(outcome.trace, "contradictions", ()) or ())
        if contradictions > cfg.max_contradictions:
            continue

        rels = _extract_relations_from_equation(outcome)
        triples = _triples_from_relations(rels)
        unique_triples = list(dict.fromkeys(triples))
        for i in range(len(unique_triples)):
            for j in range(len(unique_triples)):
                if i == j:
                    continue
                cooc_counter[(unique_triples[i], unique_triples[j])] += 1

    by_rhs: Dict[Tuple[str, str, str], list[Tuple[Tuple[str, str, str], int]]] = defaultdict(list)
    for (lhs, rhs), count in cooc_counter.items():
        if count >= cfg.min_support:
            by_rhs[rhs].append((lhs, count))

    specs: List[RuleSpec] = []
    for rhs, lhs_items in by_rhs.items():
        lhs_items.sort(key=lambda x: -x[1])
        for lhs, support in lhs_items:
            lhs_rel, _, _ = lhs
            rhs_rel, _, _ = rhs
            spec = RuleSpec(
                if_all=[{"rel": lhs_rel, "args": ["?X", "?Y"]}],
                then={"rel": rhs_rel, "args": ["?X", "?Y"]},
                source="auto_evo.cooc",
                support=int(support),
            )
            specs.append(spec)
            if len(specs) >= cfg.max_new_rules_per_cycle:
                return specs
    return specs
