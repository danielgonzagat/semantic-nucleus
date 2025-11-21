"""Auto-evolution utilities layered on top of the NSR core."""

from .api import run_text_learning
from .episodes import Episode, append_episode, iter_episodes
from .kb_store import RuleSpec, load_rule_specs, append_rule_specs, write_rule_specs
from .induction import InductionConfig, induce_rules
from .policy import filter_novel_rules, sort_by_energy
from .energy import compute_energy, EnergyConfig, EnergyMetrics
from .loop import (
    AutoEvoConfig,
    register_and_evolve,
    energy_based_evolution_cycle,
    EnergyEvolutionReport,
)
from .genome import (
    GenomeEntry,
    GenomeSummary,
    load_genome,
    summarize_genome,
    set_rule_disabled,
)
from .env_kb import (
    EnvironmentKB,
    load_env_kb,
    make_session_for_env,
    promote_kb_version,
    rollback_kb_version,
    rules_path_for_version,
    write_current_version,
)

__all__ = [
    "run_text_learning",
    "Episode",
    "append_episode",
    "iter_episodes",
    "RuleSpec",
    "load_rule_specs",
    "append_rule_specs",
    "write_rule_specs",
    "InductionConfig",
    "induce_rules",
    "filter_novel_rules",
    "sort_by_energy",
    "compute_energy",
    "EnergyConfig",
    "EnergyMetrics",
    "AutoEvoConfig",
    "register_and_evolve",
    "energy_based_evolution_cycle",
    "EnergyEvolutionReport",
    "GenomeEntry",
    "GenomeSummary",
    "load_genome",
    "summarize_genome",
    "set_rule_disabled",
    "EnvironmentKB",
    "load_env_kb",
    "make_session_for_env",
    "promote_kb_version",
    "rollback_kb_version",
    "rules_path_for_version",
    "write_current_version",
]
