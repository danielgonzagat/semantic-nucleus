"""
META-SANDBOX v1.0 — snapshot determinístico do MetaState.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass

from .state import MetaState


@dataclass(slots=True)
class MetaSandbox:
    """
    Mantém um snapshot independente do MetaState e permite
    executar um runtime isolado.
    """

    snapshot_state: MetaState

    @classmethod
    def from_state(cls, state: MetaState) -> "MetaSandbox":
        cloned = copy.deepcopy(state)
        return cls(snapshot_state=cloned)

    def spawn_runtime(self):
        """
        Cria um MetaRuntime isolado baseado no snapshot.
        Importação local para evitar dependência circular.
        """
        from metanucleus.runtime.meta_runtime import MetaRuntime

        return MetaRuntime(state=self.snapshot_state)
