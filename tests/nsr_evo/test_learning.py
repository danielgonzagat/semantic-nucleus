import json
import os
from pathlib import Path
import subprocess
import sys

from nsr import run_text_full, SessionCtx
from nsr_evo.episodes import Episode, append_episode, iter_episodes
from nsr_evo.api import run_text_learning
from nsr_evo.kb_store import load_rule_specs


def test_episode_log_roundtrip(tmp_path):
    session = SessionCtx()
    outcome = run_text_full("Um carro existe", session)
    episode = Episode.from_outcome("Um carro existe", outcome, kb_version="test")
    log_path = tmp_path / "episodes.jsonl"
    append_episode(log_path, episode)
    entries = list(iter_episodes(log_path))
    assert entries
    assert entries[0]["text"] == "Um carro existe"
    assert entries[0]["kb_version"] == "test"


def test_run_text_learning_creates_episode(tmp_path):
    episodes_path = tmp_path / "eps.jsonl"
    rules_path = tmp_path / "rules.jsonl"
    answer, outcome = run_text_learning(
        "O carro tem roda",
        episodes_path=episodes_path,
        rules_path=rules_path,
        kb_version="unit-test",
    )
    assert "carro" in answer.lower()
    assert outcome.answer == answer
    assert episodes_path.exists()
    with episodes_path.open() as handle:
        lines = handle.readlines()
    assert len(lines) == 1


def test_cli_cycle_runs(tmp_path):
    episodes_path = tmp_path / "episodes.jsonl"
    rules_path = tmp_path / "rules.jsonl"
    # Gera alguns episódios
    for _ in range(3):
        run_text_learning(
            "O carro anda rápido",
            episodes_path=episodes_path,
            rules_path=rules_path,
        )
    cmd = [
        sys.executable,
        "-m",
        "nsr_evo.cli_cycle",
        "--episodes",
        str(episodes_path),
        "--rules",
        str(rules_path),
        "--max-prompts",
        "2",
        "--max-rules",
        "2",
    ]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path.cwd() / "src")
    result = subprocess.run(cmd, capture_output=True, text=True, check=True, env=env)
    assert "[nsr_evo]" in result.stdout


def test_cli_genome_toggle(tmp_path):
    rules_path = tmp_path / "rules.jsonl"
    payload = {
        "if_all": [{"rel": "REL_A", "args": ["?X", "?Y"]}],
        "then": {"rel": "REL_B", "args": ["?X", "?Y"]},
        "source": "test",
        "support": 1,
        "energy_gain": 0.5,
        "accepted_at": 123.0,
        "version": 1,
        "disabled": False,
    }
    rules_path.write_text(json.dumps(payload) + "\n", encoding="utf-8")

    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path.cwd() / "src")
    list_cmd = [
        sys.executable,
        "-m",
        "nsr_evo.cli_genome",
        "list",
        "--rules",
        str(rules_path),
    ]
    result = subprocess.run(list_cmd, capture_output=True, text=True, check=True, env=env)
    assert "rules total=1" in result.stdout

    toggle_cmd = [
        sys.executable,
        "-m",
        "nsr_evo.cli_genome",
        "toggle",
        "--rules",
        str(rules_path),
        "--index",
        "0",
        "--disable",
    ]
    subprocess.run(toggle_cmd, capture_output=True, text=True, check=True, env=env)
    specs = load_rule_specs(rules_path)
    assert specs[0].disabled is True
