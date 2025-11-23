"""
Módulos de integração externa (GitHub, CI, etc) do Metanúcleo.
"""

from .github_client import GitHubClient, GitHubConfig, GitHubError
from .evolution_pr import EvolutionPRManager

__all__ = [
    "GitHubClient",
    "GitHubConfig",
    "GitHubError",
    "EvolutionPRManager",
]
