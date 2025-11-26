"""
Motor determinístico de autoevolução supervisionada.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import shutil
import subprocess
import tempfile
from time import perf_counter
from typing import Any, Callable, Iterable, List, Optional, Sequence

from metanucleus.utils.diff_apply import apply_unified_diff, DiffApplyError


# ---------------------------------------------------------------------------
# Modelos centrais
# ---------------------------------------------------------------------------


@dataclass()
class PatchCandidate:
    id: str
    title: str
    description: str
    diff: str
    metadata: dict[str, Any] | None = None


@dataclass()
class TestRunResult:
    success: bool
    return_code: int
    duration_sec: float
    stdout: str
    stderr: str


@dataclass()
class PatchEvaluation:
    candidate: PatchCandidate
    test_result: TestRunResult | None
    score: float
    notes: dict[str, Any] = field(default_factory=dict)
    sandbox_path: Optional[Path] = None


@dataclass()
class EvolutionConfig:
    project_root: Path
    test_command: Sequence[str]
    max_candidates: int = 3
    keep_sandboxes: bool = False
    use_git_apply: bool = True

    def __post_init__(self) -> None:
        self.project_root = Path(self.project_root).resolve()
        if not self.project_root.exists():
            raise ValueError(f"Project root inexistente: {self.project_root}")
        if not self.test_command:
            raise ValueError("test_command não pode ser vazio.")
        self.test_command = tuple(str(token) for token in self.test_command)


# ---------------------------------------------------------------------------
# Execução de testes
# ---------------------------------------------------------------------------


class ShellTestCore:
    """
    Executa uma bateria de testes determinística via subprocess.
    """

    def __init__(self, project_root: Path, command: Sequence[str]):
        self.project_root = Path(project_root).resolve()
        self.command = tuple(command)

    def run(self, *, cwd: Optional[Path] = None) -> TestRunResult:
        exec_cwd = cwd or self.project_root
        start = perf_counter()
        proc = subprocess.run(
            self.command,
            cwd=exec_cwd,
            capture_output=True,
            text=True,
            check=False,
        )
        duration = perf_counter() - start
        return TestRunResult(
            success=proc.returncode == 0,
            return_code=proc.returncode,
            duration_sec=duration,
            stdout=proc.stdout,
            stderr=proc.stderr,
        )


# ---------------------------------------------------------------------------
# Motor principal
# ---------------------------------------------------------------------------

SuggestCallback = Callable[[], Iterable[PatchCandidate]]
ApprovalCallback = Callable[[PatchEvaluation], bool]


class SupervisedEvolutionEngine:
    """
    Orquestra o ciclo:
        1. coletar candidatos a patch
        2. aplicar cada patch em um sandbox isolado
        3. executar testes
        4. retornar o melhor candidato aprovado
    """

    def __init__(
        self,
        config: EvolutionConfig,
        test_core: ShellTestCore,
        suggest_patches: SuggestCallback,
        approval_fn: ApprovalCallback | None = None,
    ):
        self.config = config
        self.test_core = test_core
        self.suggest = suggest_patches
        self.approval_fn = approval_fn or (lambda ev: ev.test_result is not None and ev.test_result.success)

    def step(self) -> dict[str, Any]:
        evaluations: List[PatchEvaluation] = []
        candidates = list(self.suggest())[: self.config.max_candidates]
        for candidate in candidates:
            evaluation = self._evaluate_candidate(candidate)
            evaluations.append(evaluation)
        chosen = next((ev for ev in evaluations if self.approval_fn(ev)), None)
        return {
            "evaluations": evaluations,
            "chosen": chosen,
        }

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _evaluate_candidate(self, candidate: PatchCandidate) -> PatchEvaluation:
        sandbox_parent = Path(tempfile.mkdtemp(prefix="metanucleus-evo-"))
        sandbox_path = sandbox_parent / "workspace"
        notes: dict[str, Any] = {}
        test_result: TestRunResult | None = None
        score = 0.0

        try:
            self._prepare_sandbox(sandbox_path)
            self._apply_diff_to_sandbox(candidate.diff, sandbox_path)
            test_result = self.test_core.run(cwd=sandbox_path)
            score = 1.0 if test_result.success else 0.0
        except DiffApplyError as exc:
            notes["diff_error"] = str(exc)
        except Exception as exc:  # pragma: no cover - proteção extra
            notes["exception"] = str(exc)
        finally:
            if not self.config.keep_sandboxes:
                shutil.rmtree(sandbox_parent, ignore_errors=True)

        return PatchEvaluation(
            candidate=candidate,
            test_result=test_result,
            score=score,
            notes=notes,
            sandbox_path=sandbox_path if self.config.keep_sandboxes else None,
        )

    def _prepare_sandbox(self, sandbox_path: Path) -> None:
        shutil.copytree(
            self.config.project_root,
            sandbox_path,
            dirs_exist_ok=False,
            ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc", "*.pyo"),
        )

    def _apply_diff_to_sandbox(self, diff: str, sandbox_path: Path) -> None:
        if not diff.strip():
            raise DiffApplyError("Diff vazio recebido para avaliação.")
        application = apply_unified_diff(sandbox_path, diff)
        for rel_path, content in application.updated_files.items():
            target = sandbox_path / rel_path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
        for rel_path in application.deleted_files:
            target = sandbox_path / rel_path
            if target.exists():
                if target.is_file():
                    target.unlink()
                elif target.is_dir():
                    shutil.rmtree(target)


__all__ = [
    "EvolutionConfig",
    "PatchCandidate",
    "PatchEvaluation",
    "ShellTestCore",
    "SupervisedEvolutionEngine",
    "TestRunResult",
]
