"""
Ferramentas determinísticas para interpretar e aplicar diffs unificados.

Essas rotinas são utilizadas tanto pelo motor de evolução quanto pelo
integrador GitHub para transformar representações `diff --git` em arquivos
concretos que podem ser comitados ou enviados via API.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import re
from pathlib import Path
from typing import Dict, List, Tuple


class DiffParseError(RuntimeError):
    """Erro lançado quando o diff não segue o formato esperado."""


class DiffApplyError(RuntimeError):
    """Erro lançado ao aplicar um diff em um arquivo base."""


@dataclass()
class HunkLine:
    op: str  # " ", "+", "-"
    text: str


@dataclass()
class Hunk:
    old_start: int
    old_length: int
    new_start: int
    new_length: int
    lines: List[HunkLine] = field(default_factory=list)


@dataclass()
class FilePatch:
    old_path: str
    new_path: str
    hunks: List[Hunk] = field(default_factory=list)
    newline_at_end: bool | None = None

    @property
    def is_new_file(self) -> bool:
        return self.old_path == "/dev/null"

    @property
    def is_deleted_file(self) -> bool:
        return self.new_path == "/dev/null"

    @property
    def target_path(self) -> str:
        """
        Caminho final após aplicar o patch, normalizado para remover prefixos
        `a/` ou `b/`.
        """

        raw = self.new_path if not self.is_deleted_file else self.old_path
        return _normalize_patch_path(raw)

    @property
    def source_path(self) -> str:
        raw = self.old_path if not self.is_new_file else self.new_path
        return _normalize_patch_path(raw)


_HUNK_RE = re.compile(r"@@ -(?P<old_start>\d+)(?:,(?P<old_len>\d+))? \+(?P<new_start>\d+)(?:,(?P<new_len>\d+))? @@")


def _parse_hunk_header(header_line: str) -> Hunk:
    match = _HUNK_RE.match(header_line)
    if not match:
        raise DiffParseError(f"Cabeçalho de hunk inválido: {header_line!r}")
    old_start = int(match.group("old_start"))
    new_start = int(match.group("new_start"))
    old_len = int(match.group("old_len") or "1")
    new_len = int(match.group("new_len") or "1")
    return Hunk(
        old_start=old_start,
        old_length=old_len,
        new_start=new_start,
        new_length=new_len,
    )


def parse_unified_diff(diff_text: str) -> List[FilePatch]:
    """
    Converte uma string em formato unified diff em estruturas FilePatch.
    Suporta múltiplos arquivos em um único diff.
    """

    patches: List[FilePatch] = []
    current_patch: FilePatch | None = None
    current_hunk: Hunk | None = None
    last_line_op: str | None = None

    lines = diff_text.splitlines()
    idx = 0

    def flush_hunk() -> None:
        nonlocal current_hunk
        if current_patch is not None and current_hunk is not None:
            current_patch.hunks.append(current_hunk)
        current_hunk = None

    def flush_patch() -> None:
        nonlocal current_patch
        flush_hunk()
        if current_patch is not None:
            patches.append(current_patch)
        current_patch = None

    while idx < len(lines):
        line = lines[idx]
        if line.startswith("diff --git"):
            flush_patch()
            idx += 1
            continue
        if line.startswith("--- "):
            flush_patch()
            old_path = line[4:].strip()
            idx += 1
            if idx >= len(lines) or not lines[idx].startswith("+++ "):
                raise DiffParseError("Linha '+++' esperada após linha '---'")
            new_path = lines[idx][4:].strip()
            current_patch = FilePatch(old_path=old_path, new_path=new_path)
            idx += 1
            continue
        if line.startswith("@@"):
            if current_patch is None:
                raise DiffParseError("Bloco @@ encontrado antes de declarar arquivo.")
            flush_hunk()
            current_hunk = _parse_hunk_header(line)
            last_line_op = None
            idx += 1
            while idx < len(lines):
                entry = lines[idx]
                if entry.startswith("diff --git") or entry.startswith("--- ") or entry.startswith("@@"):
                    break
                if entry.startswith("\\ No newline at end of file"):
                    if current_patch is not None and last_line_op == "+":
                        current_patch.newline_at_end = False
                    idx += 1
                    continue
                if not entry:
                    raise DiffParseError("Linha vazia inesperada dentro de um hunk.")
                op = entry[0]
                if op not in {" ", "+", "-"}:
                    raise DiffParseError(f"Prefixo de linha desconhecido em hunk: {entry!r}")
                text = entry[1:]
                if current_hunk is None:
                    raise DiffParseError("Linha de hunk sem cabeçalho @@ correspondente.")
                current_hunk.lines.append(HunkLine(op=op, text=text))
                last_line_op = op
                idx += 1
            continue
        idx += 1

    flush_patch()
    return patches


def apply_patch_to_text(original_text: str, file_patch: FilePatch) -> str:
    """
    Aplica um FilePatch em um texto base e retorna o conteúdo resultante.
    """

    original_lines, original_trailing_newline = _split_text_lines(original_text)
    new_lines: List[str] = []
    src_idx = 0

    for hunk in file_patch.hunks:
        expected_idx = hunk.old_start - 1
        if expected_idx < 0:
            raise DiffApplyError("Índice inicial inválido no hunk.")
        while src_idx < expected_idx:
            if src_idx >= len(original_lines):
                raise DiffApplyError("Hunk refere-se a linhas além do final do arquivo.")
            new_lines.append(original_lines[src_idx])
            src_idx += 1
        for hline in hunk.lines:
            if hline.op == " ":
                if src_idx >= len(original_lines) or original_lines[src_idx] != hline.text:
                    raise DiffApplyError("Contexto incompatível ao aplicar diff.")
                new_lines.append(hline.text)
                src_idx += 1
            elif hline.op == "-":
                if src_idx >= len(original_lines) or original_lines[src_idx] != hline.text:
                    raise DiffApplyError("Linha removida não corresponde ao arquivo base.")
                src_idx += 1
            elif hline.op == "+":
                new_lines.append(hline.text)
            else:  # pragma: no cover - validação já ocorre no parse
                raise DiffApplyError(f"Operador de patch desconhecido: {hline.op}")

    new_lines.extend(original_lines[src_idx:])

    newline_setting: bool
    if file_patch.newline_at_end is not None:
        newline_setting = file_patch.newline_at_end
    else:
        if file_patch.is_new_file:
            newline_setting = True
        else:
            newline_setting = original_trailing_newline

    result = "\n".join(new_lines)
    if new_lines and newline_setting:
        result += "\n"
    elif not new_lines:
        result = "" if not newline_setting else "\n"
    return result


@dataclass()
class DiffApplication:
    """
    Resultado de aplicar um diff completo em um repositório local.
    """

    updated_files: Dict[str, str]
    deleted_files: Tuple[str, ...]


def apply_unified_diff(repo_root: Path, diff_text: str) -> DiffApplication:
    """
    Aplica um diff unificado em disco e retorna os conteúdos resultantes, sem
    gravar alterações. Útil para enviar os arquivos diretamente via API.
    """

    patches = parse_unified_diff(diff_text)
    updated: Dict[str, str] = {}
    deleted: List[str] = []

    for patch in patches:
        target_path = patch.target_path
        source_path = patch.source_path
        if not target_path:
            raise DiffApplyError("Caminho alvo vazio no patch.")
        source_file = repo_root / source_path if source_path else None
        original_text = ""
        if not patch.is_new_file:
            if source_file is None or not source_file.exists():
                raise DiffApplyError(f"Arquivo base não encontrado: {source_path}")
            original_text = source_file.read_text(encoding="utf-8")
        if patch.is_deleted_file:
            if target_path:
                deleted.append(target_path)
            continue
        new_text = apply_patch_to_text(original_text, patch)
        updated[target_path] = new_text
        if patch.is_new_file and target_path in deleted:
            deleted.remove(target_path)
        if (not patch.is_new_file) and source_path and source_path != target_path:
            deleted.append(source_path)

    dedup_deleted: List[str] = []
    seen: set[str] = set()
    for path in deleted:
        if path and path not in seen:
            dedup_deleted.append(path)
            seen.add(path)

    return DiffApplication(updated_files=updated, deleted_files=tuple(dedup_deleted))


def _split_text_lines(text: str) -> Tuple[List[str], bool]:
    if not text:
        return [], False
    if text.endswith("\n"):
        return text[:-1].split("\n"), True
    return text.split("\n"), False


def _normalize_patch_path(path: str) -> str:
    if path in {"", "/dev/null"}:
        return ""
    if path.startswith("a/") or path.startswith("b/"):
        path = path[2:]
    while path.startswith("./"):
        path = path[2:]
    return path.strip()


__all__ = [
    "DiffApplication",
    "DiffApplyError",
    "DiffParseError",
    "FilePatch",
    "Hunk",
    "HunkLine",
    "apply_patch_to_text",
    "apply_unified_diff",
    "parse_unified_diff",
]
