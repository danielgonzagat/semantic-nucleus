from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List

from liu import relation, entity, var
from nsr import Rule


@dataclass()
class RuleSpec:
    """Representação serializável de uma regra simbólica."""

    if_all: list[dict]
    then: dict
    source: str = "auto_evo"
    support: int = 1
    energy_gain: float = 0.0
    accepted_at: float | None = None
    version: int | None = None
    disabled: bool = False


def _node_from_pattern(pattern: dict):
    rel = pattern.get("rel") or pattern.get("label") or "REL"
    args_nodes = []
    for arg in pattern.get("args", []):
        if isinstance(arg, str) and arg.startswith("?"):
            args_nodes.append(var(arg))
        else:
            args_nodes.append(entity(str(arg)))
    return relation(rel, *args_nodes)


def rule_from_spec(spec: RuleSpec) -> Rule:
    conds = tuple(_node_from_pattern(p) for p in spec.if_all)
    then_node = _node_from_pattern(spec.then)
    return Rule(if_all=conds, then=then_node)


def load_rule_specs(path: Path) -> list[RuleSpec]:
    if not path.exists():
        return []
    specs: List[RuleSpec] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                specs.append(
                    RuleSpec(
                        if_all=list(data["if_all"]),
                        then=dict(data["then"]),
                        source=str(data.get("source", "auto_evo")),
                        support=int(data.get("support", 1)),
                        energy_gain=float(data.get("energy_gain", 0.0)),
                        accepted_at=data.get("accepted_at"),
                        version=data.get("version"),
                        disabled=bool(data.get("disabled", False)),
                    )
                )
            except Exception:
                continue
    return specs


def append_rule_specs(path: Path, specs: Iterable[RuleSpec]) -> None:
    specs = list(specs)
    if not specs:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        for spec in specs:
            payload = {
                "if_all": spec.if_all,
                "then": spec.then,
                "source": spec.source,
                "support": spec.support,
                "energy_gain": spec.energy_gain,
                "accepted_at": spec.accepted_at,
                "version": spec.version,
                "disabled": spec.disabled,
            }
            json.dump(payload, handle, ensure_ascii=False, separators=(",", ":"))
            handle.write("\n")


def write_rule_specs(path: Path, specs: Iterable[RuleSpec]) -> None:
    specs = list(specs)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for spec in specs:
            payload = {
                "if_all": spec.if_all,
                "then": spec.then,
                "source": spec.source,
                "support": spec.support,
                "energy_gain": spec.energy_gain,
                "accepted_at": spec.accepted_at,
                "version": spec.version,
                "disabled": spec.disabled,
            }
            json.dump(payload, handle, ensure_ascii=False, separators=(",", ":"))
            handle.write("\n")


def next_rule_version(specs: Iterable[RuleSpec]) -> int:
    versions = [spec.version or 0 for spec in specs]
    return (max(versions) if versions else 0) + 1
