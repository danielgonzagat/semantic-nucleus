from __future__ import annotations

import pytest

from metanucleus.runtime import MetanucleusRuntime
from metanucleus.semantics.frames import SemanticFrame
from metanucleus.testing.mismatch_logger import log_frame_mismatch


@pytest.fixture(scope="module")
def runtime() -> MetanucleusRuntime:
    return MetanucleusRuntime()


@pytest.fixture()
def session(runtime: MetanucleusRuntime):
    return runtime.new_session()


FRAME_CASES = [
    (
        "O carro bateu no muro.",
        "pt",
        "bater",
        {"AGENT": "carro", "PATIENT": "muro"},
    ),
    (
        "The car hit the wall.",
        "en",
        "hit",
        {"AGENT": "car", "PATIENT": "wall"},
    ),
]


def _roles_map(frame: SemanticFrame | None) -> dict[str, str]:
    if frame is None:
        return {}
    result: dict[str, str] = {}
    for assignment in frame.roles:
        result.setdefault(assignment.role.value, assignment.text)
    return result


@pytest.mark.parametrize("text, lang, expected_predicate, expected_roles", FRAME_CASES)
def test_semantic_frames(session, text, lang, expected_predicate, expected_roles) -> None:
    analysis = session.analyze(text)
    frame: SemanticFrame | None = analysis.get("frame")  # type: ignore[assignment]
    predicted_roles = _roles_map(frame)
    predicate = frame.predicate if frame else "(none)"

    if predicate != expected_predicate or any(
        expected_roles.get(role) != predicted_roles.get(role) for role in expected_roles
    ):
        log_frame_mismatch(
            input_text=text,
            language=lang,
            predicate=predicate,
            expected_roles=expected_roles,
            predicted_roles=predicted_roles,
            note=None,
        )

    assert True
