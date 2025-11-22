"""
Persistência determinística de fatos e regras do Logic-Engine em formato LIU-like.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Dict, Iterable, List, Tuple

from .logic_engine import LogicEngine, LogicRule, normalize_statement


@dataclass(frozen=True)
class LogicSnapshot:
    facts: Dict[str, bool]
    rules: Tuple[LogicRule, ...]


def serialize_logic_engine(engine: LogicEngine) -> str:
    payload = {
        "facts": engine.facts,
        "rules": [
            {"premises": list(rule.premises), "conclusion": rule.conclusion}
            for rule in engine.rules
        ],
    }
    return json.dumps(payload, sort_keys=True, ensure_ascii=False)


def deserialize_logic_engine(serialized: str) -> LogicEngine:
    payload = json.loads(serialized)
    engine = LogicEngine()
    for key, truth in payload.get("facts", {}).items():
        engine.add_fact(key, truth)
    for rule_payload in payload.get("rules", []):
        premises = tuple(rule_payload.get("premises") or ())
        conclusion = rule_payload.get("conclusion") or ""
        if premises and conclusion:
            engine.add_rule(premises, conclusion)
    return engine


def logic_snapshot(engine: LogicEngine) -> LogicSnapshot:
    return LogicSnapshot(facts=dict(engine.facts), rules=tuple(engine.rules))


__all__ = ["LogicSnapshot", "serialize_logic_engine", "deserialize_logic_engine", "logic_snapshot"]
