"""
Validador determinístico para pacotes de idioma usados pelo IAN-Ω.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Sequence, Tuple

from .langpacks import (
    ConjugationSpec,
    DialogRuleSpec,
    LanguagePack,
    LexemeSpec,
    SyntacticPatternSpec,
)


@dataclass(frozen=True)
class ValidationIssue:
    severity: str  # "error" | "warning"
    message: str

    def __post_init__(self) -> None:
        if self.severity not in {"error", "warning"}:
            raise ValueError(f"Invalid severity '{self.severity}'")

    @property
    def is_error(self) -> bool:
        return self.severity == "error"


def validate_pack(pack: LanguagePack) -> List[ValidationIssue]:
    issues: List[ValidationIssue] = []
    issues.extend(_check_lexemes(pack.code, pack.lexemes))
    issues.extend(_check_dialog_rules(pack.code, pack.dialog_rules, pack.conjugations))
    issues.extend(_check_conjugations(pack.code, pack.conjugations))
    issues.extend(_check_patterns(pack.code, pack.syntactic_patterns))
    if not pack.lexemes:
        issues.append(
            ValidationIssue("error", f"{pack.code}: language pack must contain at least one lexeme")
        )
    if not pack.dialog_rules:
        issues.append(
            ValidationIssue("warning", f"{pack.code}: language pack defines no dialog rules")
        )
    return issues


def has_errors(issues: Iterable[ValidationIssue]) -> bool:
    return any(issue.is_error for issue in issues)


def _check_lexemes(code: str, lexemes: Sequence[LexemeSpec]) -> List[ValidationIssue]:
    issues: List[ValidationIssue] = []
    for lex in lexemes:
        for form in lex.forms:
            if form != form.upper():
                issues.append(
                    ValidationIssue(
                        "error",
                        f"{code}: lexeme '{lex.lemma}' form '{form}' must be uppercase",
                    )
                )
        if not lex.semantics.isupper():
            issues.append(
                ValidationIssue(
                    "warning",
                    f"{code}: lexeme '{lex.lemma}' semantics '{lex.semantics}' should be uppercase",
                )
            )
    return issues


def _check_dialog_rules(
    code: str,
    rules: Sequence[DialogRuleSpec],
    conjugations: Sequence[ConjugationSpec],
) -> List[ValidationIssue]:
    issues: List[ValidationIssue] = []
    conj_keys = {
        (entry.lemma.lower(), entry.tense.lower(), str(entry.person), entry.number.lower())
        for entry in conjugations
    }
    for rule in rules:
        if not rule.surface_tokens:
            issues.append(
                ValidationIssue(
                    "error", f"{code}: dialog rule '{rule.reply_role}' has no surface tokens"
                )
            )
        for token in rule.surface_tokens:
            if token.startswith(":CONJ:"):
                parts = token.split(":")
                if len(parts) != 6:
                    issues.append(
                        ValidationIssue(
                            "error",
                            f"{code}: rule '{rule.reply_role}' has malformed conjugation token '{token}'",
                        )
                    )
                    continue
                _, _, lemma, tense, person, number = parts
                key = (lemma.lower(), tense.lower(), person, number.lower())
                if key not in conj_keys:
                    issues.append(
                        ValidationIssue(
                            "warning",
                            f"{code}: rule '{rule.reply_role}' references missing conjugation for {lemma}/{tense}/{person}/{number}",
                        )
                    )
    return issues


def _check_conjugations(code: str, conjugations: Sequence[ConjugationSpec]) -> List[ValidationIssue]:
    issues: List[ValidationIssue] = []
    seen: set[Tuple[str, str, str, str]] = set()
    for entry in conjugations:
        key = (
            entry.lemma.lower(),
            entry.tense.lower(),
            str(entry.person),
            entry.number.lower(),
        )
        if key in seen:
            issues.append(
                ValidationIssue(
                    "error",
                    f"{code}: duplicate conjugation for {entry.lemma}/{entry.tense}/{entry.person}/{entry.number}",
                )
            )
        seen.add(key)
    return issues


def _check_patterns(code: str, patterns: Sequence[SyntacticPatternSpec]) -> List[ValidationIssue]:
    issues: List[ValidationIssue] = []
    for pattern in patterns:
        if not pattern.sequence:
            issues.append(
                ValidationIssue("warning", f"{code}: syntactic pattern '{pattern.name}' is empty")
            )
        for semantic in pattern.sequence:
            if semantic != semantic.upper():
                issues.append(
                    ValidationIssue(
                        "warning",
                        f"{code}: pattern '{pattern.name}' semantic '{semantic}' should be uppercase",
                    )
                )
    return issues


__all__ = ["ValidationIssue", "validate_pack", "has_errors"]
