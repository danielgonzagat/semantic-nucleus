"""
Metanúcleo determinístico — núcleo simbólico experimental.
"""

from .core.state import MetaState
from .runtime.meta_runtime import MetaRuntime

__all__ = ["MetaRuntime", "MetaState"]
