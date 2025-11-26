"""Runs evaluation and auto-evolution in a single cycle."""
from __future__ import annotations

from .eval_harness import run_eval_suite
from .auto_evolution.intent_auto_evolve import auto_evolve_intent_patterns
from .auto_evolution.frames_auto_evolve import auto_evolve_frames


def run_auto_cycle() -> None:
    print("[auto-cycle] Avaliando...\n")
    run_eval_suite()
    print("\n[auto-cycle] Evoluindo padrões de intenção...")
    intent_result = auto_evolve_intent_patterns()
    print(intent_result)
    print("\n[auto-cycle] Evoluindo padrões de frames...")
    frame_result = auto_evolve_frames()
    print(frame_result)


def main() -> int:
    run_auto_cycle()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
