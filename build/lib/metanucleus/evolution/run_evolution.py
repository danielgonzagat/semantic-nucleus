"""
Entrypoint determinístico para rodar uma rodada de autoevolução integrada ao GitHub.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import List
import uuid

from metanucleus.integration.github_client import GitHubClient, GitHubConfig
from metanucleus.integration.evolution_pr import EvolutionPRManager
from metanucleus.evolution.supervised_evolution import (
    SupervisedEvolutionEngine,
    EvolutionConfig,
    ShellTestCore,
    PatchCandidate,
    PatchEvaluation,
)
from metanucleus.kernel.meta_kernel import MetaKernel


def suggest_patches_from_kernel(kernel: MetaKernel) -> List[PatchCandidate]:
    """
    Hook central para gerar patches.

    Nesta versão inicial permitimos injetar um diff determinístico via:
      - variável METANUCLEUS_DIFF contendo o diff completo
      - variável METANUCLEUS_DIFF_PATH apontando para um arquivo .diff
    """

    _ = kernel
    diff_text = os.environ.get("METANUCLEUS_DIFF")
    candidate_id = os.environ.get("METANUCLEUS_DIFF_ID")
    title = os.environ.get("METANUCLEUS_DIFF_TITLE", "Patch evolutivo importado")
    description = os.environ.get(
        "METANUCLEUS_DIFF_DESC",
        "Diff fornecido manualmente para avaliação determinística.",
    )

    diff_path = os.environ.get("METANUCLEUS_DIFF_PATH")
    if diff_path:
        path = Path(diff_path)
        if not path.exists():
            raise FileNotFoundError(f"METANUCLEUS_DIFF_PATH não encontrado: {path}")
        diff_text = path.read_text(encoding="utf-8")
        candidate_id = candidate_id or path.stem
        title = title or f"Patch {path.name}"

    if not diff_text:
        return []

    candidate_id = candidate_id or f"auto-{uuid.uuid4().hex[:8]}"
    return [
        PatchCandidate(
            id=candidate_id,
            title=title,
            description=description,
            diff=diff_text,
        )
    ]


def approval_auto(ev: PatchEvaluation) -> bool:
    """
    Aprovação automática: aceita apenas patches com testes verdes.
    """

    if ev.test_result is None:
        return False
    return ev.test_result.success


def main() -> None:
    root = Path(__file__).resolve().parents[2]
    kernel = MetaKernel.bootstrap()

    evo_cfg = EvolutionConfig(
        project_root=root,
        test_command=["pytest", "-q"],
        max_candidates=3,
        keep_sandboxes=False,
        use_git_apply=False,
    )
    test_core = ShellTestCore(project_root=root, command=evo_cfg.test_command)

    evo_engine = SupervisedEvolutionEngine(
        config=evo_cfg,
        test_core=test_core,
        suggest_patches=lambda: suggest_patches_from_kernel(kernel),
        approval_fn=approval_auto,
    )

    result = evo_engine.step()
    chosen = result.get("chosen")

    if not chosen:
        print("[EVO] Nenhum patch aprovado nesta rodada.")
        return

    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise RuntimeError("GITHUB_TOKEN não definido para criação do PR.")

    github_cfg = GitHubConfig(
        owner=os.environ.get("GITHUB_OWNER", "danielgonzagat"),
        repo=os.environ.get("GITHUB_REPO", "metanucleus"),
        token=token,
        api_url=os.environ.get("GITHUB_API_URL", "https://api.github.com"),
    )
    client = GitHubClient(cfg=github_cfg)
    pr_manager = EvolutionPRManager(client=client, repo_root=root)
    pr = pr_manager.open_pr_from_patch(chosen)
    print("[EVO] Pull Request criado:", pr.get("html_url", "(sem URL)"))


if __name__ == "__main__":
    main()
