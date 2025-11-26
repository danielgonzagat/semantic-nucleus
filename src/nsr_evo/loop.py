from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, List, Sequence

from nsr import SessionCtx, run_text_full
from nsr.state import Rule
from nsr_evo.episodes import Episode, append_episode, iter_episodes
from nsr_evo.induction import EpisodeView, InductionConfig, induce_rules
from nsr_evo.kb_store import (
    RuleSpec,
    load_rule_specs,
    rule_from_spec,
    append_rule_specs,
    next_rule_version,
)
from nsr_evo.policy import filter_novel_rules, sort_by_energy
from nsr_evo.energy import compute_energy, EnergyConfig


@dataclass()
class AutoEvoConfig:
    episodes_path: Path
    rules_path: Path
    max_induction_prompts: int = 16
    induction_cfg: InductionConfig = field(default_factory=InductionConfig)
    max_rules_per_cycle: int = 4


def _load_system_rules() -> tuple[Rule, ...]:
    base_session = SessionCtx()
    return tuple(getattr(base_session, "kb_rules", ()))


def _load_learned_rules(path: Path) -> tuple[Rule, ...]:
    specs = load_rule_specs(path)
    active_specs = [spec for spec in specs if not spec.disabled]
    return tuple(rule_from_spec(spec) for spec in active_specs)


def _recent_prompts(path: Path, limit: int) -> list[str]:
    prompts = []
    for payload in iter_episodes(path):
        text = str(payload.get("text") or "").strip()
        if text:
            prompts.append(text)
    return prompts[-limit:]


def _episode_views_for_prompts(
    prompts: Iterable[str],
    kb_rules: Sequence[Rule],
    limit: int,
) -> list[EpisodeView]:
    views: List[EpisodeView] = []
    for text in prompts:
        session = SessionCtx(kb_rules=tuple(kb_rules))
        outcome = run_text_full(text, session)
        views.append(EpisodeView(text=text, outcome=outcome))
        if len(views) >= limit:
            break
    return views


def register_and_evolve(
    text: str,
    outcome,
    cfg: AutoEvoConfig,
    kb_version: str | None = None,
) -> list[RuleSpec]:
    episode = Episode.from_outcome(text, outcome, kb_version=kb_version)
    append_episode(cfg.episodes_path, episode)

    system_rules = _load_system_rules()
    learned_rules = _load_learned_rules(cfg.rules_path)
    merged_rules = system_rules + learned_rules

    prompts = _recent_prompts(cfg.episodes_path, cfg.max_induction_prompts)
    views = [EpisodeView(text=text, outcome=outcome)]
    extra_prompts = [prompt for prompt in prompts if prompt != text]
    views.extend(
        _episode_views_for_prompts(extra_prompts, merged_rules, cfg.max_induction_prompts - 1)
    )

    proposed = induce_rules(views, cfg.induction_cfg)
    if not proposed:
        return []

    existing_specs = load_rule_specs(cfg.rules_path)
    novel = filter_novel_rules(proposed, existing_specs)
    ordered = sort_by_energy(novel)
    accepted = ordered[: cfg.max_rules_per_cycle]
    if not accepted:
        return []
    base_version = next_rule_version(existing_specs)
    now = time.time()
    for idx, spec in enumerate(accepted):
        spec.version = base_version + idx
        spec.accepted_at = now
        spec.disabled = False
    append_rule_specs(cfg.rules_path, accepted)
    return accepted


@dataclass()
class EnergyEvolutionReport:
    considered_prompts: int
    candidate_rules: int
    accepted_rules: int
    base_energy: float
    new_energy: float
    improved: bool


def energy_based_evolution_cycle(
    *,
    episodes_path: Path,
    rules_path: Path,
    max_prompts: int = 32,
    induction_cfg: InductionConfig | None = None,
    energy_cfg: EnergyConfig | None = None,
) -> EnergyEvolutionReport:
    prompts = _recent_prompts(episodes_path, max_prompts)
    if not prompts:
        return EnergyEvolutionReport(0, 0, 0, 0.0, 0.0, False)

    system_rules = _load_system_rules()
    learned_rules = _load_learned_rules(rules_path)
    base_rules = system_rules + learned_rules

    base_metrics = compute_energy(
        prompts,
        base_rules=base_rules,
        base_ontology=SessionCtx().kb_ontology,
        config=energy_cfg,
    )

    cfg = induction_cfg or InductionConfig()
    views = _episode_views_for_prompts(prompts, base_rules, cfg.max_new_rules_per_cycle * 2)
    proposed = induce_rules(views, cfg)
    if not proposed:
        return EnergyEvolutionReport(
            considered_prompts=len(prompts),
            candidate_rules=0,
            accepted_rules=0,
            base_energy=base_metrics.value,
            new_energy=base_metrics.value,
            improved=False,
        )

    novel = filter_novel_rules(proposed, load_rule_specs(rules_path))
    ordered = sort_by_energy(novel)
    candidate_rules = ordered[: cfg.max_new_rules_per_cycle]
    if not candidate_rules:
        return EnergyEvolutionReport(
            considered_prompts=len(prompts),
            candidate_rules=len(proposed),
            accepted_rules=0,
            base_energy=base_metrics.value,
            new_energy=base_metrics.value,
            improved=False,
        )

    mutated_rules = base_rules + tuple(rule_from_spec(spec) for spec in candidate_rules)

    new_metrics = compute_energy(
        prompts,
        base_rules=mutated_rules,
        base_ontology=SessionCtx().kb_ontology,
        config=energy_cfg,
    )

    improved = new_metrics.value < base_metrics.value
    accepted = len(candidate_rules) if improved else 0
    if improved:
        existing_specs = load_rule_specs(rules_path)
        base_version = next_rule_version(existing_specs)
        now = time.time()
        delta = base_metrics.value - new_metrics.value
        per_rule_gain = delta / max(1, len(candidate_rules))
        for idx, spec in enumerate(candidate_rules):
            spec.version = base_version + idx
            spec.accepted_at = now
            spec.disabled = False
            spec.energy_gain = per_rule_gain
        append_rule_specs(rules_path, candidate_rules)

    return EnergyEvolutionReport(
        considered_prompts=len(prompts),
        candidate_rules=len(proposed),
        accepted_rules=accepted,
        base_energy=base_metrics.value,
        new_energy=new_metrics.value,
        improved=improved,
    )
