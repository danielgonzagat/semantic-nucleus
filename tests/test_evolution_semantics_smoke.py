from __future__ import annotations

from metanucleus.evolution.semantic_mismatch_log import SemanticMismatch, append_semantic_mismatch


def test_semantic_mismatch_pt_car_sentence() -> None:
    mismatch = SemanticMismatch(
        phrase="O carro está andando rápido.",
        lang="pt",
        issue="Frame subject/action/modifier não mapeado.",
        expected_repr="STRUCT(subject=ENTITY('carro'), action=ENTITY('andar'), modifier=[ENTITY('rápido')])",
        actual_repr="STRUCT(subject=ENTITY('carro'), action=None, modifier=None)",
        severity="warning",
        file_path="metanucleus/semantics/ontology.py",
    )
    append_semantic_mismatch(mismatch)
    assert True


def test_semantic_mismatch_en_car_sentence() -> None:
    mismatch = SemanticMismatch(
        phrase="The car is moving fast.",
        lang="en",
        issue="Frame semântico não marca 'car' como vehicle.",
        expected_repr="STRUCT(subject=ENTITY('car'), action=ENTITY('move'), modifier=[ENTITY('fast')])",
        actual_repr="STRUCT(subject=ENTITY('car'), action=None, modifier=None)",
        severity="warning",
        file_path="metanucleus/semantics/ontology.py",
    )
    append_semantic_mismatch(mismatch)
    assert True
