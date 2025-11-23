"""
Gerador de patches internos (v2) baseado em análise sintática determinística.
"""

from __future__ import annotations

import ast
import difflib
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from metanucleus.evolution.supervised_evolution import PatchCandidate


@dataclass
class CodeUnit:
    """
    Representa um arquivo de código acompanhado do AST parseado.
    """

    path: Path
    source: str
    tree: ast.AST


@dataclass
class PhiFunctionInfo:
    """
    Metadados determinísticos sobre uma função Φ (phi_*).
    """

    name: str
    module_path: str
    file_path: Path


class MetaPatchGenerator:
    """
    Gera patches autônomos para docstrings, registro de operadores Φ e testes.
    """

    def __init__(self, project_root: Path):
        self.project_root = project_root.resolve()
        self.src_root = self._resolve_src_root()
        self.tests_root = self._resolve_tests_root()
        self.module_base = self.src_root.parent if self.src_root else self.project_root

    # ------------------------------------------------------------------
    # Entrada principal
    # ------------------------------------------------------------------

    def generate_candidates(self, max_candidates: int = 5) -> List[PatchCandidate]:
        units = self._scan_codebase()
        phi_infos = self._collect_phi_functions(units)

        patches: List[PatchCandidate] = []

        for unit in units:
            doc_patches = self._docstring_patches_for_unit(unit)
            for patch in doc_patches:
                patches.append(patch)
                if len(patches) >= max_candidates:
                    return patches

        registry_patches = self._phi_registry_patches(units, phi_infos)
        for patch in registry_patches:
            patches.append(patch)
            if len(patches) >= max_candidates:
                return patches

        test_patch = self._phi_tests_patch(phi_infos)
        if test_patch is not None:
            patches.append(test_patch)

        return patches[:max_candidates]

    # ------------------------------------------------------------------
    # Scan helpers
    # ------------------------------------------------------------------

    def _resolve_src_root(self) -> Path:
        candidates = [
            self.project_root / "metanucleus",
            self.project_root / "src" / "metanucleus",
            self.project_root.parent / "metanucleus",
        ]
        for candidate in candidates:
            if candidate.exists():
                return candidate
        return (self.project_root / "metanucleus").resolve()

    def _resolve_tests_root(self) -> Path:
        candidates = [
            self.project_root / "tests",
            self.project_root.parent / "tests",
            self.src_root.parent / "tests",
            self.src_root.parent.parent / "tests",
        ]
        for candidate in candidates:
            if candidate.exists():
                return candidate
        return (self.project_root / "tests").resolve()

    def _scan_codebase(self) -> List[CodeUnit]:
        units: List[CodeUnit] = []
        if not self.src_root.exists():
            return units
        for path in sorted(self.src_root.rglob("*.py")):
            if "tests" in path.parts:
                continue
            try:
                source = path.read_text(encoding="utf-8")
                tree = ast.parse(source, filename=str(path))
                units.append(CodeUnit(path=path, source=source, tree=tree))
            except Exception:
                continue
        return units

    # ------------------------------------------------------------------
    # Coleta de funções Φ
    # ------------------------------------------------------------------

    def _collect_phi_functions(self, units: List[CodeUnit]) -> List[PhiFunctionInfo]:
        infos: List[PhiFunctionInfo] = []
        for unit in units:
            module_path = self._module_path_for(unit.path)
            for node in ast.walk(unit.tree):
                if isinstance(node, ast.FunctionDef) and node.name.startswith("phi_"):
                    infos.append(
                        PhiFunctionInfo(
                            name=node.name,
                            module_path=module_path,
                            file_path=unit.path,
                        )
                    )
        return infos

    def _module_path_for(self, file_path: Path) -> str:
        try:
            rel = file_path.relative_to(self.module_base)
        except ValueError:
            rel = file_path
        parts = list(rel.parts)
        if parts and parts[-1].endswith(".py"):
            parts[-1] = parts[-1][:-3]
        return ".".join(parts)

    # ------------------------------------------------------------------
    # Docstrings semânticas
    # ------------------------------------------------------------------

    def _docstring_patches_for_unit(self, unit: CodeUnit) -> List[PatchCandidate]:
        issues: List[PatchCandidate] = []
        if not self._is_core_file(unit.path):
            return issues

        fn_nodes = [n for n in unit.tree.body if isinstance(n, ast.FunctionDef)]
        class_nodes = [n for n in unit.tree.body if isinstance(n, ast.ClassDef)]

        for fn in fn_nodes:
            if ast.get_docstring(fn):
                continue
            if not self._is_important_function(fn.name):
                continue
            patched_source = self._add_function_docstring(unit.source, fn)
            if patched_source and patched_source != unit.source:
                diff = self._make_diff(unit.path, unit.source, patched_source)
                issues.append(
                    PatchCandidate(
                        id=f"docfn-{unit.path.name}-{fn.name}",
                        title=f"Adicionar docstring semântica à função {fn.name}",
                        description=(
                            f"Função `{fn.name}` em `{unit.path}` integra o fluxo determinístico "
                            "do núcleo e não possui docstring. Este patch insere uma descrição automática."
                        ),
                        diff=diff,
                    )
                )

        for cls in class_nodes:
            if ast.get_docstring(cls):
                continue
            if not self._is_important_class(cls.name):
                continue
            patched_source = self._add_class_docstring(unit.source, cls)
            if patched_source and patched_source != unit.source:
                diff = self._make_diff(unit.path, unit.source, patched_source)
                issues.append(
                    PatchCandidate(
                        id=f"doccls-{unit.path.name}-{cls.name}",
                        title=f"Adicionar docstring semântica à classe {cls.name}",
                        description=(
                            f"Classe `{cls.name}` em `{unit.path}` aparenta ser parte da arquitetura central "
                            "sem docstring. Patch adiciona uma descrição determinística pré-formatada."
                        ),
                        diff=diff,
                    )
                )

        return issues

    def _is_core_file(self, path: Path) -> bool:
        keywords = [
            "kernel",
            "meta",
            "semantics",
            "runtime",
            "evolution",
            "liu",
            "calculus",
            "phi",
        ]
        lower = str(path).lower()
        return any(key in lower for key in keywords)

    def _is_important_function(self, name: str) -> bool:
        lowers = name.lower()
        if lowers.startswith(("meta_", "semantic_", "phi_", "run_", "evolve_")):
            return True
        return lowers in {"step", "respond", "handle_turn", "dispatch_phi", "analyze"}

    def _is_important_class(self, name: str) -> bool:
        lowers = name.lower()
        core = {
            "metakernel",
            "isr",
            "semanticengine",
            "supervisedevolutionengine",
            "metacalculus",
        }
        if lowers in (entry.lower() for entry in core):
            return True
        return "kernel" in lowers or "engine" in lowers or "runtime" in lowers

    def _add_function_docstring(self, source: str, fn: ast.FunctionDef) -> Optional[str]:
        lines = source.splitlines()
        def_line_idx = fn.lineno - 1
        indent = self._infer_indent(lines[def_line_idx] if def_line_idx < len(lines) else "")
        doc = self._build_fn_docstring(fn.name)
        insert_line = def_line_idx + 1
        new_lines = lines[:insert_line] + [f"{indent}    \"\"\"{doc}\"\"\""] + lines[insert_line:]
        return "\n".join(new_lines) + "\n"

    def _add_class_docstring(self, source: str, cls: ast.ClassDef) -> Optional[str]:
        lines = source.splitlines()
        class_idx = cls.lineno - 1
        indent = self._infer_indent(lines[class_idx] if class_idx < len(lines) else "")
        doc = self._build_cls_docstring(cls.name)
        insert_line = class_idx + 1
        new_lines = lines[:insert_line] + [f"{indent}    \"\"\"{doc}\"\"\""] + lines[insert_line:]
        return "\n".join(new_lines) + "\n"

    def _infer_indent(self, line: str) -> str:
        return line[: len(line) - len(line.lstrip())]

    def _build_fn_docstring(self, name: str) -> str:
        base = (
            "Função determinística do núcleo responsável por uma etapa simbólica "
            "no pipeline do Metanúcleo."
        )
        lower = name.lower()
        if lower.startswith("meta_"):
            return "[auto] " + base + " Atua na coordenação meta."
        if lower.startswith("semantic_"):
            return "[auto] " + base + " Opera sobre interpretações semânticas."
        if lower.startswith("phi_"):
            return "[auto] " + base + " Implementa um operador Φ sobre o ISR."
        if lower.startswith("evolve_"):
            return "[auto] " + base + " Relaciona-se ao ciclo de autoevolução."
        if lower in {"step", "respond"}:
            return "[auto] " + base + " Avança um ciclo cognitivo completo."
        return "[auto] " + base

    def _build_cls_docstring(self, name: str) -> str:
        base = (
            "Componente estrutural central do núcleo simbólico-determinístico, "
            "responsável por manter comportamento estável e auditável."
        )
        lower = name.lower()
        if "kernel" in lower:
            return "[auto] " + base + " Atua como orquestrador global."
        if "engine" in lower:
            return "[auto] " + base + " Executa ciclos determinísticos sobre o estado."
        if "runtime" in lower:
            return "[auto] " + base + " Encapsula estado e interação com o ambiente."
        return "[auto] " + base

    # ------------------------------------------------------------------
    # Registro de operadores Φ
    # ------------------------------------------------------------------

    def _phi_registry_patches(
        self,
        units: List[CodeUnit],
        phi_infos: List[PhiFunctionInfo],
    ) -> List[PatchCandidate]:
        patches: List[PatchCandidate] = []
        phi_by_file: dict[Path, List[PhiFunctionInfo]] = {}
        for info in phi_infos:
            phi_by_file.setdefault(info.file_path, []).append(info)

        for unit in units:
            functions = phi_by_file.get(unit.path)
            if not functions:
                continue
            if "PHI_OPS" not in unit.source:
                continue
            missing = self._phi_missing_registrations(unit.source, functions)
            if not missing:
                continue
            patched_source = self._append_phi_registry_lines(unit.source, missing)
            diff = self._make_diff(unit.path, unit.source, patched_source)
            patches.append(
                PatchCandidate(
                    id=f"phi-reg-{unit.path.name}",
                    title=f"Registrar operadores Φ ausentes em {unit.path.name}",
                    description=(
                        "Registra automaticamente os operadores Φ definidos no arquivo mas "
                        "ausentes em `PHI_OPS`. Operadores: " + ", ".join(missing)
                    ),
                    diff=diff,
                )
            )
        return patches

    def _phi_missing_registrations(
        self,
        source: str,
        phi_list: List[PhiFunctionInfo],
    ) -> List[str]:
        missing: List[str] = []
        for info in phi_list:
            if self._phi_is_registered_in_source(source, info.name):
                continue
            missing.append(info.name)
        return missing

    def _phi_is_registered_in_source(self, source: str, name: str) -> bool:
        patterns = [
            f'PHI_OPS["{name}"]',
            f"PHI_OPS['{name}']",
            f"PHI_OPS[{name!r}]",
        ]
        return any(pattern in source for pattern in patterns)

    def _append_phi_registry_lines(self, source: str, missing: List[str]) -> str:
        lines = source.splitlines()
        if lines and lines[-1].strip():
            lines.append("")
        lines.append("# [auto] Metanúcleo: registro automático de Φ ausentes")
        for name in missing:
            lines.append(f'PHI_OPS["{name}"] = {name}')
        return "\n".join(lines) + "\n"

    # ------------------------------------------------------------------
    # Testes automáticos
    # ------------------------------------------------------------------

    def _phi_tests_patch(self, phi_infos: List[PhiFunctionInfo]) -> Optional[PatchCandidate]:
        if not phi_infos:
            return None

        self.tests_root.mkdir(parents=True, exist_ok=True)
        test_file = self.tests_root / "test_phi_ops_auto.py"
        original = ""
        if test_file.exists():
            original = test_file.read_text(encoding="utf-8")

        updated = original
        for info in phi_infos:
            test_name = f"test_{info.name}_auto"
            if test_name in updated:
                continue
            snippet = self._build_phi_test_snippet(info)
            if updated and not updated.endswith("\n"):
                updated += "\n"
            updated += ("\n" if updated else "") + snippet + "\n"

        if updated == original:
            return None

        diff = self._make_diff(test_file, original, updated)
        phi_names = ", ".join(sorted({info.name for info in phi_infos}))
        return PatchCandidate(
            id="phi-tests-auto",
            title="Criar/atualizar testes automáticos para operadores Φ",
            description=(
                "Garante que cada operador Φ possua um teste stub em `tests/test_phi_ops_auto.py`. "
                f"Operadores cobertos: {phi_names}."
            ),
            diff=diff,
        )

    def _build_phi_test_snippet(self, info: PhiFunctionInfo) -> str:
        return (
            f"def test_{info.name}_auto():\n"
            f"    \"\"\"[auto] Verifica se {info.name} está acessível e é chamável.\"\"\"\n"
            f"    from {info.module_path} import {info.name}\n"
            f"    assert callable({info.name})\n"
        )

    # ------------------------------------------------------------------
    # Diff utilitário
    # ------------------------------------------------------------------

    def _make_diff(self, path: Path, old: str, new: str) -> str:
        old_lines = old.splitlines(keepends=True)
        new_lines = new.splitlines(keepends=True)
        diff_lines = difflib.unified_diff(
            old_lines,
            new_lines,
            fromfile=f"a/{path}",
            tofile=f"b/{path}",
        )
        return "".join(diff_lines)


__all__ = [
    "MetaPatchGenerator",
    "PhiFunctionInfo",
    "CodeUnit",
]
