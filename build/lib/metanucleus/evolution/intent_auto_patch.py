"""
Facilitador para gerar EvolutionPatch focados em intents.
"""

from __future__ import annotations

from pathlib import Path
from typing import List

from metanucleus.evolution.intent_patch_generator import IntentLexiconPatchGenerator
from metanucleus.evolution.types import EvolutionPatch
from metanucleus.utils.project import get_project_root


def suggest_intent_patches(max_candidates: int | None = None) -> List[EvolutionPatch]:
    """
    Converte IntentLexiconPatchCandidate em EvolutionPatch padronizados.
    """
    project_root = get_project_root(Path(__file__))
    generator = IntentLexiconPatchGenerator(project_root=project_root)
    limit = max_candidates or 5
    candidates = generator.generate_patches(max_candidates=limit)
    patches: List[EvolutionPatch] = []
    for cand in candidates:
        patches.append(
            EvolutionPatch(
                domain="intent",
                title=cand.title,
                description=cand.description,
                diff=cand.diff,
                meta={"source": "intent_auto_patch"},
            )
        )
    return patches


__all__ = ["suggest_intent_patches"]
