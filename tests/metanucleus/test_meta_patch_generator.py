from __future__ import annotations

from pathlib import Path

from metanucleus.evolution.meta_patch_generator import IntentLogEntry, MetaPatchGenerator

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_generate_from_logs_enriches_intent_keywords() -> None:
    generator = MetaPatchGenerator(project_root=PROJECT_ROOT)
    logs = [
        IntentLogEntry(
            text="Onde fica a biblioteca central?",
            detected="greeting",
            expected="question",
            lang="pt",
        )
    ]
    patches = generator.generate_from_logs(logs, max_candidates=1)
    assert patches, "Esperava pelo menos um patch de enriquecimento"
    assert "intent_config.py" in patches[0].diff
    assert "onde" in patches[0].diff
