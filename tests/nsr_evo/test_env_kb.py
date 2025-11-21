import json
import os
import subprocess
import sys
from pathlib import Path

from nsr import SessionCtx
from nsr_evo import env_kb


def _write_rule(path: Path, rel_suffix: str = "A", disabled: bool = False) -> None:
    payload = {
        "if_all": [{"rel": f"REL_{rel_suffix}", "args": ["?X"]}],
        "then": {"rel": f"NEXT_{rel_suffix}", "args": ["?X"]},
        "source": "unit",
        "support": 2,
        "energy_gain": 0.4,
        "accepted_at": 123.0,
        "version": 1,
        "disabled": disabled,
    }
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")


def test_load_env_kb_reads_version_and_filters_disabled(tmp_path, monkeypatch):
    env_root = tmp_path / ".nsr_learning"
    dev_dir = env_root / "dev"
    dev_dir.mkdir(parents=True, exist_ok=True)
    (dev_dir / "current_kb.json").write_text(json.dumps({"version": 1}), encoding="utf-8")
    rules_path = dev_dir / "learned_rules_v1.jsonl"
    _write_rule(rules_path, rel_suffix="A", disabled=False)
    with rules_path.open("a", encoding="utf-8") as handle:
        payload = {
            "if_all": [{"rel": "REL_DISABLED", "args": ["?X"]}],
            "then": {"rel": "NEXT_DISABLED", "args": ["?X"]},
            "disabled": True,
        }
        handle.write(json.dumps(payload) + "\n")

    monkeypatch.setattr(env_kb, "ENV_ROOT", env_root, raising=False)
    env_kb._system_rules.cache_clear()

    kb_snapshot = env_kb.load_env_kb("dev")
    base_rules = tuple(SessionCtx().kb_rules)

    assert kb_snapshot.version == 1
    assert kb_snapshot.rules_path == rules_path
    assert len(kb_snapshot.rules) == len(base_rules) + 1


def test_promote_and_rollback_helpers(tmp_path, monkeypatch):
    env_root = tmp_path / ".nsr_learning"
    dev_dir = env_root / "dev"
    dev_dir.mkdir(parents=True, exist_ok=True)
    rules_path = dev_dir / "learned_rules_v2.jsonl"
    _write_rule(rules_path, rel_suffix="B", disabled=False)
    (dev_dir / "current_kb.json").write_text(json.dumps({"version": 2}), encoding="utf-8")

    monkeypatch.setattr(env_kb, "ENV_ROOT", env_root, raising=False)
    env_kb._system_rules.cache_clear()

    dst = env_kb.promote_kb_version("dev", "staging", 2)
    assert dst.exists()
    cfg = json.loads((env_root / "staging" / "current_kb.json").read_text(encoding="utf-8"))
    assert cfg["version"] == 2

    # simulate manual change and rollback
    (env_root / "staging" / "current_kb.json").write_text(json.dumps({"version": 0}), encoding="utf-8")
    env_kb.rollback_kb_version("staging", 2)
    cfg = json.loads((env_root / "staging" / "current_kb.json").read_text(encoding="utf-8"))
    assert cfg["version"] == 2


def test_cli_promote_and_rollback(tmp_path):
    repo_root = Path(__file__).resolve().parents[2]
    env_dir = tmp_path / ".nsr_learning" / "dev"
    env_dir.mkdir(parents=True, exist_ok=True)
    rules_path = env_dir / "learned_rules_v1.jsonl"
    _write_rule(rules_path, rel_suffix="C", disabled=False)
    (env_dir / "current_kb.json").write_text(json.dumps({"version": 1}), encoding="utf-8")

    env = os.environ.copy()
    env["PYTHONPATH"] = str(repo_root / "src")

    promote_cmd = [
        sys.executable,
        "-m",
        "nsr_evo.cli_promote_kb",
        "--from-env",
        "dev",
        "--to-env",
        "staging",
        "--version",
        "1",
    ]
    subprocess.run(
        promote_cmd,
        check=True,
        capture_output=True,
        text=True,
        cwd=tmp_path,
        env=env,
    )

    staging_cfg = json.loads(
        (tmp_path / ".nsr_learning" / "staging" / "current_kb.json").read_text(encoding="utf-8")
    )
    assert staging_cfg["version"] == 1

    rollback_cmd = [
        sys.executable,
        "-m",
        "nsr_evo.cli_rollback_kb",
        "--env",
        "staging",
        "--to-version",
        "1",
    ]
    subprocess.run(
        rollback_cmd,
        check=True,
        capture_output=True,
        text=True,
        cwd=tmp_path,
        env=env,
    )

    staging_cfg = json.loads(
        (tmp_path / ".nsr_learning" / "staging" / "current_kb.json").read_text(encoding="utf-8")
    )
    assert staging_cfg["version"] == 1
