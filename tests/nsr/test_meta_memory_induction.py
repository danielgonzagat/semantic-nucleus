import json

from nsr import SessionCtx, run_text_full
from nsr.meta_memory_induction import record_episode, run_memory_induction


def test_memory_induction_generates_rule_from_episodes(tmp_path):
    episodes_path = tmp_path / "episodes.jsonl"
    suggestions_path = tmp_path / "rules.jsonl"
    session = SessionCtx()
    session.config.memory_store_path = None
    session.config.episodes_path = None
    outcome1 = run_text_full("Um carro existe", session)
    record_episode(str(episodes_path), "Um carro existe", outcome1)
    outcome2 = run_text_full("O carro tem roda", session)
    record_episode(str(episodes_path), "O carro tem roda", outcome2)
    run_memory_induction(
        episodes_path=str(episodes_path),
        suggestions_path=str(suggestions_path),
        episode_limit=8,
        min_support=1,
    )
    assert suggestions_path.exists()
    with suggestions_path.open() as handle:
        lines = [line.strip() for line in handle if line.strip()]
    assert lines
    payload = json.loads(lines[0])
    assert "if_rel" in payload and "then_rel" in payload
    assert payload["support"] >= 1
