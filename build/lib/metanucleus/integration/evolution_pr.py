"""
Conversor PatchEvaluation → Pull Request real no GitHub.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Any

from metanucleus.integration.github_client import GitHubClient
from metanucleus.utils.diff_apply import apply_unified_diff, DiffApplyError
from metanucleus.evolution.supervised_evolution import PatchEvaluation


@dataclass(slots=True)
class EvolutionPRManager:
    client: GitHubClient
    repo_root: Path

    def open_pr_from_patch(self, ev: PatchEvaluation) -> Dict[str, Any]:
        if not ev.candidate.diff.strip():
            raise ValueError("Diff vazio não pode originar um PR.")

        branch_name = f"evo/{ev.candidate.id}"
        self.client.create_branch(new_branch=branch_name, from_branch="main")
        changed_files = self._apply_diff_via_api(ev.candidate.diff, branch_name)
        body = self._build_pr_body(ev, changed_files)

        return self.client.create_pull_request(
            title=ev.candidate.title,
            body=body,
            head_branch=branch_name,
            base_branch="main",
            draft=False,
        )

    def _apply_diff_via_api(self, diff: str, branch_name: str) -> List[str]:
        application = apply_unified_diff(self.repo_root, diff)
        touched: List[str] = []
        for path, content in application.updated_files.items():
            norm_path = path.replace("\\", "/")
            self.client.create_or_update_file(
                path=norm_path,
                content=content,
                message=f"Autoevolution patch applied: {norm_path}",
                branch=branch_name,
            )
            touched.append(norm_path)
        for path in application.deleted_files:
            norm_path = path.replace("\\", "/")
            self.client.delete_file(
                path=norm_path,
                message=f"Autoevolution patch removed: {norm_path}",
                branch=branch_name,
            )
            touched.append(norm_path)
        if not touched:
            raise DiffApplyError("Diff não aplicou nenhuma modificação em arquivo.")
        return touched

    def _build_pr_body(self, ev: PatchEvaluation, touched_files: List[str]) -> str:
        lines: List[str] = []
        lines.append(f"### Patch Evolutivo: `{ev.candidate.id}`")
        lines.append("")
        if ev.candidate.description:
            lines.append(ev.candidate.description)
            lines.append("")
        lines.append("### Arquivos afetados")
        for path in touched_files:
            lines.append(f"- `{path}`")
        lines.append("")
        lines.append("### Diff proposto")
        lines.append("```diff")
        lines.append(ev.candidate.diff.strip())
        lines.append("```")
        lines.append("")
        if ev.test_result:
            lines.append("### Testes no Sandbox")
            lines.append(f"- success: `{ev.test_result.success}`")
            lines.append(f"- return_code: `{ev.test_result.return_code}`")
            lines.append(f"- duration: `{ev.test_result.duration_sec:.2f}s`")
            if ev.test_result.stdout:
                lines.append("")
                lines.append("<details>")
                lines.append("<summary>stdout</summary>")
                lines.append("")
                lines.append("```")
                lines.append(ev.test_result.stdout.strip() or "(vazio)")
                lines.append("```")
                lines.append("</details>")
            if ev.test_result.stderr:
                lines.append("")
                lines.append("<details>")
                lines.append("<summary>stderr</summary>")
                lines.append("")
                lines.append("```")
                lines.append(ev.test_result.stderr.strip() or "(vazio)")
                lines.append("```")
                lines.append("</details>")
            lines.append("")
        lines.append("### Explicação Semântica")
        lines.append("- Patch gerado determinísticamente pelo Metanúcleo.")
        lines.append(f"- Score evolutivo: `{ev.score:.4f}`")
        return "\n".join(lines)


__all__ = [
    "EvolutionPRManager",
]
