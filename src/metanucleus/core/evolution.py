"""
META-EVOLUTION v1.0 — pipeline simbólico determinístico para otimizar código.

Este módulo executa o fluxo:
    Código → AST → LIU → META-ANÁLISE → Otimização → Código novo
e valida o resultado com testes de regressão determinísticos antes de propor
um patch humano-explicável.
"""

from __future__ import annotations

import ast
import copy
import difflib
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from dataclasses import dataclass, field

from .ast_bridge import python_code_to_liu
from .liu import Node, NodeKind


# ---------------------------------------------------------------------------
# Estruturas de domínio
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class MetaAnalysis:
    """Resumo estrutural do código analisado."""

    redundant_terms: List[str]
    cost_before: int
    cost_after: int
    liu_repr: str


@dataclass(slots=True)
class EvolutionResult:
    """Retorno completo de uma tentativa de evolução."""

    success: bool
    reason: str
    optimized_source: Optional[str] = None
    diff: Optional[str] = None
    analysis: Optional[MetaAnalysis] = None
    original_source: Optional[str] = None


@dataclass(slots=True)
class EvolutionRequest:
    """Representa um alvo de evolução específico."""

    source: str
    function_name: str
    samples: Sequence[Tuple[Any, ...]] = field(
        default_factory=lambda: [(0,), (1,), (2,), (5,), (-3,)]
    )


# ---------------------------------------------------------------------------
# Utilidades internas
# ---------------------------------------------------------------------------


def _load_function_ast(module_ast: ast.Module, func_name: str) -> ast.FunctionDef:
    for node in module_ast.body:
        if isinstance(node, ast.FunctionDef) and node.name == func_name:
            return node
    raise ValueError(f"Função '{func_name}' não encontrada no módulo analisado.")


def _extract_single_return(func: ast.FunctionDef) -> ast.Return:
    returns = [stmt for stmt in func.body if isinstance(stmt, ast.Return)]
    if len(returns) != 1:
        raise ValueError(
            "A evolução v1.0 suporta apenas funções com um único 'return'."
        )
    if returns[0].value is None:
        raise ValueError("Return sem expressão não pode ser otimizado.")
    return returns[0]


def _is_number_node(node: ast.AST) -> bool:
    return isinstance(node, ast.Constant) and isinstance(node.value, (int, float))


def _to_float(value: Any) -> float:
    if isinstance(value, bool):
        return float(int(value))
    return float(value)


@dataclass
class _TermData:
    coefficient: float
    base: Optional[ast.AST]
    key: str


def _collect_terms(expr: ast.AST) -> List[Tuple[float, Optional[ast.AST]]]:
    if isinstance(expr, ast.BinOp):
        if isinstance(expr.op, ast.Add):
            return _collect_terms(expr.left) + _collect_terms(expr.right)
        if isinstance(expr.op, ast.Sub):
            right_terms = [(-coeff, base) for coeff, base in _collect_terms(expr.right)]
            return _collect_terms(expr.left) + right_terms
    coeff, base = _split_term(expr)
    return [(coeff, base)]


def _split_term(node: ast.AST) -> Tuple[float, Optional[ast.AST]]:
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mult):
        if _is_number_node(node.left) and not _is_number_node(node.right):
            return _to_float(node.left.value), copy.deepcopy(node.right)
        if _is_number_node(node.right) and not _is_number_node(node.left):
            return _to_float(node.right.value), copy.deepcopy(node.left)
        if _is_number_node(node.left) and _is_number_node(node.right):
            return _to_float(node.left.value) * _to_float(node.right.value), None
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        coeff, base = _split_term(node.operand)
        return -coeff, base
    if _is_number_node(node):
        return _to_float(node.value), None
    return 1.0, copy.deepcopy(node)


def _reduce_terms(terms: Iterable[Tuple[float, Optional[ast.AST]]]) -> Dict[str, _TermData]:
    aggregated: Dict[str, _TermData] = {}
    for coeff, base in terms:
        if base is None:
            key = "CONST"
        else:
            key = ast.dump(base, include_attributes=False)
        data = aggregated.get(key)
        if data is None:
            aggregated[key] = _TermData(coefficient=coeff, base=base, key=key)
        else:
            data.coefficient += coeff
    # remove ruído insignificante
    filtered = {
        key: data for key, data in aggregated.items() if abs(data.coefficient) > 1e-9
    }
    return filtered


def _number_node(value: float) -> ast.Constant:
    as_int = int(value)
    if abs(value - as_int) < 1e-9:
        return ast.Constant(value=as_int)
    return ast.Constant(value=value)


def _term_to_ast(term: _TermData) -> ast.AST:
    coeff = term.coefficient
    base = term.base
    if base is None:
        return _number_node(coeff)
    if abs(coeff - 1.0) < 1e-9:
        return copy.deepcopy(base)
    if abs(coeff + 1.0) < 1e-9:
        return ast.UnaryOp(op=ast.USub(), operand=copy.deepcopy(base))
    return ast.BinOp(
        left=_number_node(coeff),
        op=ast.Mult(),
        right=copy.deepcopy(base),
    )


def _build_expression(terms: Dict[str, _TermData]) -> ast.AST:
    if not terms:
        return ast.Constant(value=0)
    ordered = [terms[key] for key in sorted(terms.keys())]
    nodes = [_term_to_ast(term) for term in ordered]
    expr = nodes[0]
    for node in nodes[1:]:
        expr = ast.BinOp(left=expr, op=ast.Add(), right=node)
    return ast.fix_missing_locations(expr)


def _ast_cost(node: ast.AST) -> int:
    return sum(1 for _ in ast.walk(node))


def _sources_equal(a: str, b: str) -> bool:
    return a.strip() == b.strip()


def _diff_strings(original: str, optimized: str, path: str) -> str:
    diff_lines = list(
        difflib.unified_diff(
            original.splitlines(),
            optimized.splitlines(),
            fromfile=f"{path} (original)",
            tofile=f"{path} (optimized)",
            lineterm="",
        )
    )
    return "\n".join(diff_lines)


def _run_regression(
    original_src: str,
    optimized_src: str,
    function_name: str,
    samples: Sequence[Tuple[Any, ...]],
) -> bool:
    original_env: Dict[str, Any] = {}
    candidate_env: Dict[str, Any] = {}
    exec(original_src, original_env)  # noqa: S102 - execução isolada e controlada
    exec(optimized_src, candidate_env)  # noqa: S102
    original_fn = original_env.get(function_name)
    candidate_fn = candidate_env.get(function_name)
    if not callable(original_fn) or not callable(candidate_fn):
        raise ValueError("Função alvo não executável para regressão.")
    for args in samples:
        orig_out = original_fn(*args)
        cand_out = candidate_fn(*args)
        if orig_out != cand_out:
            return False
    return True


def _collect_liu_kinds(node: Node, kinds: List[str]) -> None:
    if node.kind is NodeKind.STRUCT:
        kind_field = node.fields.get("kind")
        if kind_field and kind_field.kind is NodeKind.TEXT and kind_field.label:
            kinds.append(kind_field.label)
        for child in node.fields.values():
            _collect_liu_kinds(child, kinds)
    if node.args:
        for child in node.args:
            _collect_liu_kinds(child, kinds)


def _liu_signature(node: Node, limit: int = 12) -> str:
    kinds: List[str] = []
    _collect_liu_kinds(node, kinds)
    if not kinds:
        return repr(node)
    return " > ".join(kinds[:limit])


# ---------------------------------------------------------------------------
# Interface pública
# ---------------------------------------------------------------------------


class MetaEvolution:
    """
    Implementa o pipeline de autoevolução simbólica supervisionada.

    Uso típico:
        request = EvolutionRequest(source=code_str, function_name="calcular")
        result = MetaEvolution().evolve(request)
        if result.success:
            print(result.diff)
    """

    def evolve(self, request: EvolutionRequest) -> EvolutionResult:
        module_ast = ast.parse(request.source)
        func = _load_function_ast(module_ast, request.function_name)
        return_stmt = _extract_single_return(func)

        original_expr = return_stmt.value
        assert original_expr is not None  # para mypy

        # snapshot LIU para auditoria
        func_clone = copy.deepcopy(func)
        func_module = ast.Module(body=[func_clone], type_ignores=[])
        func_source = ast.unparse(func_module)
        liu_repr = _liu_signature(python_code_to_liu(func_source))

        meta_terms = _reduce_terms(_collect_terms(original_expr))
        optimized_expr = _build_expression(meta_terms)

        if ast.dump(original_expr, include_attributes=False) == ast.dump(
            optimized_expr, include_attributes=False
        ):
            return EvolutionResult(
                success=False,
                reason="no_optimization_found",
                original_source=request.source,
            )

        # aplica nova expressão em uma cópia do módulo
        optimized_module = copy.deepcopy(module_ast)
        opt_func = _load_function_ast(optimized_module, request.function_name)
        opt_return = _extract_single_return(opt_func)
        opt_return.value = optimized_expr
        optimized_source = ast.unparse(optimized_module)

        if not _run_regression(
            request.source, optimized_source, request.function_name, request.samples
        ):
            return EvolutionResult(
                success=False,
                reason="regression_failed",
                original_source=request.source,
            )

        analysis = MetaAnalysis(
            redundant_terms=[
                term.key
                for term in meta_terms.values()
                if abs(term.coefficient) > 1 + 1e-9
            ],
            cost_before=_ast_cost(original_expr),
            cost_after=_ast_cost(optimized_expr),
            liu_repr=liu_repr,
        )

        diff = _diff_strings(
            request.source,
            optimized_source,
            path=f"{request.function_name}.py",
        )

        return EvolutionResult(
            success=True,
            reason="optimization_found",
            optimized_source=optimized_source,
            diff=diff,
            analysis=analysis,
            original_source=request.source,
        )

    def evolve_file(
        self,
        file_path: str | Path,
        function_name: str,
        samples: Optional[Sequence[Tuple[Any, ...]]] = None,
    ) -> EvolutionResult:
        path = Path(file_path)
        source = path.read_text(encoding="utf-8")
        request = EvolutionRequest(
            source=source,
            function_name=function_name,
            samples=samples or [(0,), (1,), (2,), (5,), (-3,)],
        )
        result = self.evolve(request)
        if result.success and result.optimized_source:
            result.diff = _diff_strings(
                source,
                result.optimized_source,
                path=str(path),
            )
        return result


__all__ = ["MetaEvolution", "EvolutionRequest", "EvolutionResult", "MetaAnalysis"]
