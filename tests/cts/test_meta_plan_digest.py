from __future__ import annotations

import json
from pathlib import Path

from liu import entity, struct as liu_struct, text as liu_text
from nsr.meta_transformer import MetaCalculationPlan, MetaRoute, _plan_digest
from svm.bytecode import Instruction
from svm.opcodes import Opcode
from svm.vm import Program

FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures"


def _load_fixtures() -> list[Path]:
    return sorted(FIXTURE_DIR.glob("plan_digest_*.json"))


def _plan_from_payload(payload: dict[str, object]) -> MetaCalculationPlan:
    instructions = [
        Instruction(Opcode[instruction[0]], int(instruction[1]))
        for instruction in payload["instructions"]
    ]
    constants = [
        liu_struct(tag=entity(entry["tag"]), payload=liu_text(entry["text"]))
        for entry in payload["constants"]
    ]
    program = Program(instructions=instructions, constants=constants)
    return MetaCalculationPlan(
        route=MetaRoute(payload["route"]),
        program=program,
        description=payload["description"],
    )


def test_cts_plan_digest_regressions() -> None:
    fixtures = _load_fixtures()
    assert fixtures, "Nenhum fixture CTS cadastrado para meta_plan"
    for fixture in fixtures:
        payload = json.loads(fixture.read_text(encoding="utf-8"))
        plan = _plan_from_payload(payload)
        assert _plan_digest(plan) == payload["digest"], fixture.name
