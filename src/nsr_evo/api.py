from __future__ import annotations

from pathlib import Path
from typing import Sequence, Tuple

from nsr import run_text_full, SessionCtx
from nsr.state import Rule
from nsr_evo.kb_store import load_rule_specs, rule_from_spec
from nsr_evo.loop import AutoEvoConfig, register_and_evolve


def _system_rules() -> Sequence[Rule]:
    base_session = SessionCtx()
    return tuple(getattr(base_session, "kb_rules", ()))


def _load_auto_rules(path: Path) -> Sequence[Rule]:
    specs = load_rule_specs(path)
    learned = tuple(rule_from_spec(spec) for spec in specs)
    system = _system_rules()
    return system + learned


def run_text_learning(
    text: str,
    *,
    episodes_path: Path = Path(".nsr_learning/episodes.jsonl"),
    rules_path: Path = Path(".nsr_learning/learned_rules.jsonl"),
    kb_version: str | None = None,
) -> Tuple[str, object]:
    auto_cfg = AutoEvoConfig(episodes_path=episodes_path, rules_path=rules_path)

    learned_rules = _load_auto_rules(rules_path)
    session = SessionCtx(kb_rules=tuple(learned_rules))

    outcome = run_text_full(text, session)
    register_and_evolve(text, outcome, auto_cfg, kb_version=kb_version)
    return outcome.answer, outcome
