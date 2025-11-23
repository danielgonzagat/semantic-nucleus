from __future__ import annotations

import json

from metanucleus.evolution.intent_patch_generator import IntentLexiconPatchGenerator


def test_intent_patch_generator_creates_diff(tmp_path):
    lexicon_path = tmp_path / "intent_lexicon.json"
    lexicon_path.write_text(
        json.dumps({"pt": {"question": ["por que"]}}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    log_path = tmp_path / "intent_mismatches.jsonl"
    log_entry = {
        "text": "Onde fica o metrô?",
        "expected_intent": "question",
        "actual_intent": "greeting",
        "lang": "pt",
        "source": "test",
        "timestamp": "2025-01-01T00:00:00Z",
        "extra": {},
    }
    log_path.write_text(json.dumps(log_entry, ensure_ascii=False) + "\n", encoding="utf-8")

    generator = IntentLexiconPatchGenerator(
        project_root=tmp_path,
        lexicon_path=lexicon_path,
        log_path=log_path,
    )
    patches = generator.generate_patches()
    assert patches, "deveria gerar pelo menos um patch"
    assert "onde" in patches[0].diff
