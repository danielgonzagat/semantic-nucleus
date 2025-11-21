from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence, Any

from nsr import run_text_full, SessionCtx
from nsr.state import Rule


@dataclass(slots=True)
class EnergyConfig:
    min_quality_ok: float = 0.6


@dataclass(slots=True)
class EnergyMetrics:
    total: int
    contradictions: int
    low_quality: int
    no_answer: int
    avg_quality: float
    coverage: float
    value: float


def compute_energy(
    prompts: Sequence[str],
    *,
    base_rules: Sequence[Rule] = (),
    base_ontology: Sequence[Any] = (),
    config: EnergyConfig | None = None,
) -> EnergyMetrics:
    cfg = config or EnergyConfig()
    total = contradictions = low_quality = no_answer = 0
    coverage_hits = 0
    quality_sum = 0.0

    for text in prompts:
        text = (text or "").strip()
        if not text:
            continue
        session = SessionCtx(
            kb_rules=tuple(base_rules),
            kb_ontology=tuple(base_ontology),
        )
        session.config.enable_contradiction_check = True  # type: ignore[attr-defined]
        outcome = run_text_full(text, session)
        total += 1

        q = float(outcome.quality)
        quality_sum += q

        contradictions_count = len(getattr(outcome.trace, "contradictions", ()) or ())
        if contradictions_count > 0 or str(outcome.halt_reason) == "HaltReason.CONTRADICTION":
            contradictions += 1

        ans = (outcome.answer or "").strip()
        if not ans or ans == "Não encontrei resposta.":
            no_answer += 1

        if q < cfg.min_quality_ok:
            low_quality += 1
        else:
            coverage_hits += 1

    if total == 0:
        return EnergyMetrics(
            total=0,
            contradictions=0,
            low_quality=0,
            no_answer=0,
            avg_quality=0.0,
            coverage=0.0,
            value=0.0,
        )

    avg_quality = quality_sum / total
    coverage = coverage_hits / total
    value = contradictions + low_quality + (no_answer * 0.5) - (coverage * 2.0)

    return EnergyMetrics(
        total=total,
        contradictions=contradictions,
        low_quality=low_quality,
        no_answer=no_answer,
        avg_quality=avg_quality,
        coverage=coverage,
        value=value,
    )
