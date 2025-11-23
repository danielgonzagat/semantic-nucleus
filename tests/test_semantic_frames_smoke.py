from __future__ import annotations

from metanucleus.testing.mismatch_logger import log_frame_mismatch


def test_frame_mismatch_car_pt() -> None:
    """
    Exemplo mínimo de frame PT.
    """
    log_frame_mismatch(
        input_text="O carro bateu no muro.",
        language="pt",
        predicate="bater",
        expected_roles={"AGENT": "carro", "PATIENT": "muro"},
        predicted_roles={"AGENT": "carro", "PATIENT": "parede"},
        note="placeholder smoke",
    )
    assert True


def test_frame_mismatch_car_en() -> None:
    """
    Exemplo mínimo de frame EN.
    """
    log_frame_mismatch(
        input_text="The car hit the wall.",
        language="en",
        predicate="hit",
        expected_roles={"AGENT": "car", "PATIENT": "wall"},
        predicted_roles={"AGENT": "car", "PATIENT": "barrier"},
        note="placeholder smoke",
    )
    assert True
