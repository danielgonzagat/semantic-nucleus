"""
Camada de orquestração de alto nível do Metanúcleo.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, TYPE_CHECKING

from metanucleus.core.state import MetaState
from metanucleus.core.sandbox import MetaSandbox

if TYPE_CHECKING:
    from metanucleus.runtime.meta_runtime import MetaRuntime


@dataclass(slots=True)
class MetaKernel:
    """
    Encapsula o MetaState e fornece utilitários para criar runtimes isolados.
    """

    state: MetaState

    @classmethod
    def bootstrap(cls) -> "MetaKernel":
        """
        Cria um kernel pronto para uso com estado limpo.
        """

        return cls(state=MetaState())

    def spawn_runtime(self) -> "MetaRuntime":
        """
        Retorna um MetaRuntime isolado a partir de um snapshot do estado atual.
        Importação tardia para evitar dependências circulares.
        """

        sandbox = MetaSandbox.from_state(self.state)
        return sandbox.spawn_runtime()

    def with_runtime(self, fn: Callable[["MetaRuntime"], None]) -> None:
        """
        Executa um callback com um runtime recém-criado.
        """

        runtime = self.spawn_runtime()
        fn(runtime)


__all__ = [
    "MetaKernel",
]
