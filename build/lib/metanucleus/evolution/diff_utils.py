"""
Helpers para gerar diffs unificados determinísticos.
"""

from __future__ import annotations

import difflib
from typing import List


def make_unified_diff(filename: str, original: str, patched: str) -> str:
    original_lines = original.splitlines(keepends=True)
    patched_lines = patched.splitlines(keepends=True)
    diff_lines: List[str] = list(
        difflib.unified_diff(
            original_lines,
            patched_lines,
            fromfile=f"a/{filename}",
            tofile=f"b/{filename}",
        )
    )
    return "".join(diff_lines)


__all__ = ["make_unified_diff"]
