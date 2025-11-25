"""
Auto-patch das regras de META-CALCULUS com base em calc_rule_mismatch.
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

from metanucleus.evolution.diff_utils import make_unified_diff
from metanucleus.evolution.types import EvolutionPatch
from metanucleus.utils.project import get_project_root

_ROOT = get_project_root(Path(__file__))
_LOG_PATH = _ROOT / ".metanucleus" / "mismatch_log.jsonl"
_RULES_PATH = _ROOT / "src" / "metanucleus" / "data" / "meta_calculus_rules.json"


@dataclass(slots=True)
class CalcRuleFailure:
    rule_id: str
    count: int


def _load_calc_rule_failures(max_items: int = 1000) -> List[CalcRuleFailure]:
    if not _LOG_PATH.exists():
        return []

    counter: Counter[str] = Counter()
    consumed = 0
    with _LOG_PATH.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                continue
            if data.get("type") != "calc_rule_mismatch":
                continue
            rule_id = str(data.get("rule_id") or "").strip()
            if not rule_id:
                continue
            counter[rule_id] += 1
            consumed += 1
            if consumed >= max_items:
                break

    return [CalcRuleFailure(rule_id=k, count=v) for k, v in counter.items()]


def _load_rules_config() -> Dict:
    if not _RULES_PATH.exists():
        return {
            "defaults": {
                "disable_after_failures": 5,
                "min_weight": 0.10,
                "weight_decay_per_fail": 0.15,
            },
            "rules": [],
        }
    return json.loads(_RULES_PATH.read_text(encoding="utf-8"))


def _serialize_rules_config(cfg: Dict) -> str:
    return json.dumps(cfg, indent=2, ensure_ascii=False, sort_keys=True)


def suggest_meta_calculus_patches(max_mismatches: int = 1000) -> List[EvolutionPatch]:
    failures = _load_calc_rule_failures(max_items=max_mismatches)
    if not failures:
        return []

    cfg = _load_rules_config()
    rules = cfg.get("rules", [])
    defaults = cfg.get("defaults", {})

    disable_after = int(defaults.get("disable_after_failures", 5))
    min_weight = float(defaults.get("min_weight", 0.10))
    decay_per_fail = float(defaults.get("weight_decay_per_fail", 0.15))

    rules_by_id: Dict[str, Dict] = {}
    for rule in rules:
        rid = str(rule.get("id") or "").strip()
        if rid:
            rules_by_id[rid] = rule

    updated = False
    for failure in failures:
        rule = rules_by_id.get(failure.rule_id)
        if not rule:
            continue
        fail_count = int(rule.get("fail_count", 0)) + failure.count
        weight = float(rule.get("weight", 1.0)) - decay_per_fail * failure.count
        if weight < min_weight:
            weight = min_weight

        rule["fail_count"] = fail_count
        rule["weight"] = weight
        if fail_count >= disable_after:
            rule["enabled"] = False
        updated = True

    if not updated:
        return []

    cfg["rules"] = rules
    original_text = (
        _RULES_PATH.read_text(encoding="utf-8") if _RULES_PATH.exists() else "{}\n"
    )
    updated_text = _serialize_rules_config(cfg)

    if updated_text == original_text:
        return []

    rel_path = _RULES_PATH.relative_to(_ROOT)
    diff = make_unified_diff(str(rel_path), original=original_text, patched=updated_text)

    return [
        EvolutionPatch(
            domain="meta_calculus",
            title="Atualizar regras de meta-cálculo",
            description=(
                "Ajusta fail_count, pesos e flags enabled das regras de meta-cálculo "
                "com base em calc_rule_mismatch."
            ),
            diff=diff,
            meta={
                "failures_processed": {f.rule_id: f.count for f in failures},
                "disable_after_failures": disable_after,
            },
        )
    ]


__all__ = ["suggest_meta_calculus_patches"]
