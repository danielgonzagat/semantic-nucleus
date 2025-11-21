from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Tuple

from nsr import SessionCtx
from nsr.state import Rule
from nsr_evo.kb_store import load_rule_specs, rule_from_spec


ENV_ROOT = Path(".nsr_learning")


@dataclass(slots=True, frozen=True)
class EnvironmentKB:
    """Snapshot of the knowledge base for a specific environment."""

    env: str
    version: int
    rules: Tuple[Rule, ...]
    rules_path: Path | None = None

    def make_session(self) -> SessionCtx:
        """Return a SessionCtx seeded with the environment rules."""

        return SessionCtx(kb_rules=self.rules)


def _env_dir(env: str) -> Path:
    if not env:
        raise ValueError("env name must be provided")
    return ENV_ROOT / env


def ensure_env_dir(env: str) -> Path:
    path = _env_dir(env)
    path.mkdir(parents=True, exist_ok=True)
    return path


@lru_cache(maxsize=1)
def _system_rules() -> Tuple[Rule, ...]:
    base_session = SessionCtx()
    return tuple(getattr(base_session, "kb_rules", ()))


def _read_current_version(env: str) -> int:
    cfg_path = _env_dir(env) / "current_kb.json"
    if not cfg_path.exists():
        return 0
    try:
        data = json.loads(cfg_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return 0
    version = int(data.get("version", 0))
    return max(version, 0)


def rules_path_for_version(env: str, version: int, *, ensure_dir: bool = False) -> Path:
    if version < 0:
        raise ValueError("version must be non-negative")
    base = ensure_env_dir(env) if ensure_dir else _env_dir(env)
    return base / f"learned_rules_v{version}.jsonl"


def _candidate_rule_paths(env: str, version: int) -> list[Path]:
    env_dir = _env_dir(env)
    candidates: list[Path] = [
        env_dir / f"learned_rules_v{version}.jsonl",
        env_dir / "learned_rules.jsonl",
    ]
    if env_dir != ENV_ROOT:
        candidates.append(ENV_ROOT / "learned_rules.jsonl")
    return candidates


def _load_learned_rules(env: str, version: int) -> tuple[Tuple[Rule, ...], Path | None]:
    rules_path: Path | None = None
    for candidate in _candidate_rule_paths(env, version):
        if candidate.exists():
            rules_path = candidate
            break
    specs = load_rule_specs(rules_path) if rules_path else []
    active_specs = [spec for spec in specs if not spec.disabled]
    learned = tuple(rule_from_spec(spec) for spec in active_specs)
    return learned, rules_path


def load_env_kb(env: str = "prod") -> EnvironmentKB:
    """Load the KB snapshot for a specific environment."""

    version = _read_current_version(env)
    learned_rules, rules_path = _load_learned_rules(env, version)
    all_rules = _system_rules() + learned_rules
    return EnvironmentKB(env=env, version=version, rules=all_rules, rules_path=rules_path)


def make_session_for_env(env: str = "prod") -> SessionCtx:
    """Create a SessionCtx bound to the environment knowledge base."""

    kb = load_env_kb(env)
    return SessionCtx(kb_rules=kb.rules)


def write_current_version(env: str, version: int) -> Path:
    if version < 0:
        raise ValueError("version must be non-negative")
    env_dir = ensure_env_dir(env)
    cfg_path = env_dir / "current_kb.json"
    payload = {"version": int(version)}
    cfg_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return cfg_path


def promote_kb_version(from_env: str, to_env: str, version: int) -> Path:
    """Copy a KB version between environments and activate it at the destination."""

    src = rules_path_for_version(from_env, version)
    if not src.exists():
        raise FileNotFoundError(f"rules file not found: {src}")
    dst_dir = ensure_env_dir(to_env)
    dst = dst_dir / src.name
    shutil.copy2(src, dst)
    write_current_version(to_env, version)
    return dst


def rollback_kb_version(env: str, version: int) -> Path:
    """Point an environment back to a previous KB version."""

    target = rules_path_for_version(env, version)
    if not target.exists():
        raise FileNotFoundError(f"rules file not found: {target}")
    write_current_version(env, version)
    return target


__all__ = [
    "EnvironmentKB",
    "ENV_ROOT",
    "ensure_env_dir",
    "load_env_kb",
    "make_session_for_env",
    "promote_kb_version",
    "rollback_kb_version",
    "rules_path_for_version",
    "write_current_version",
]
