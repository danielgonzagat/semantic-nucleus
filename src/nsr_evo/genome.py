from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from nsr_evo.kb_store import RuleSpec, load_rule_specs, write_rule_specs


@dataclass(slots=True)
class GenomeEntry:
    index: int
    spec: RuleSpec


@dataclass(slots=True)
class GenomeSummary:
    total: int
    active: int
    disabled: int
    avg_support: float
    avg_energy_gain: float


def load_genome(path: Path) -> list[GenomeEntry]:
    specs = load_rule_specs(path)
    return [GenomeEntry(index=i, spec=spec) for i, spec in enumerate(specs)]


def summarize_genome(path: Path) -> GenomeSummary:
    genome = load_genome(path)
    if not genome:
        return GenomeSummary(0, 0, 0, 0.0, 0.0)
    total = len(genome)
    active = sum(1 for entry in genome if not entry.spec.disabled)
    disabled = total - active
    avg_support = sum(entry.spec.support for entry in genome) / total
    avg_gain = sum(entry.spec.energy_gain for entry in genome) / total
    return GenomeSummary(total, active, disabled, avg_support, avg_gain)


def set_rule_disabled(path: Path, index: int, disabled: bool) -> None:
    genome = load_genome(path)
    if index < 0 or index >= len(genome):
        raise IndexError("rule index out of range")
    genome[index].spec.disabled = disabled
    write_rule_specs(path, [entry.spec for entry in genome])
