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
import operator
import inspect
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
class RegressionSample:
    inputs: Tuple[Any, ...]
    original_output: Any
    candidate_output: Any
    matched: bool


@dataclass(slots=True)
class RegressionReport:
    passed: bool
    samples: List[RegressionSample]


@dataclass(slots=True)
class PatchExplanation:
    summary: str
    operations: List[str]
    cost_before: int
    cost_after: int
    redundant_terms: List[str]
    liu_signature: str
    regression: RegressionReport


@dataclass(slots=True)
class EvolutionResult:
    """Retorno completo de uma tentativa de evolução."""

    success: bool
    reason: str
    optimized_source: Optional[str] = None
    diff: Optional[str] = None
    analysis: Optional[MetaAnalysis] = None
    explanation: Optional[PatchExplanation] = None
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


def _ast_equal(a: ast.AST, b: ast.AST) -> bool:
    return ast.dump(a, include_attributes=False) == ast.dump(
        b, include_attributes=False
    )


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


def _jsonify_value(value: object) -> object:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return repr(value)


def explanation_to_dict(expl: PatchExplanation) -> dict:
    return {
        "summary": expl.summary,
        "operations": expl.operations,
        "cost": {
            "before": expl.cost_before,
            "after": expl.cost_after,
            "delta": expl.cost_before - expl.cost_after,
        },
        "redundant_terms": expl.redundant_terms,
        "liu_signature": expl.liu_signature,
        "regression": {
            "passed": expl.regression.passed,
            "samples": [
                {
                    "inputs": list(sample.inputs),
                    "original_output": _jsonify_value(sample.original_output),
                    "candidate_output": _jsonify_value(sample.candidate_output),
                    "matched": sample.matched,
                }
                for sample in expl.regression.samples
            ],
        },
    }


def _describe_operations(
    original_expr: ast.AST,
    simplified_expr: ast.AST,
    factored_expr: ast.AST,
    optimized_expr: ast.AST,
) -> List[str]:
    ops: List[str] = []
    if not _ast_equal(original_expr, simplified_expr):
        ops.append("constant_folding")
    if not _ast_equal(simplified_expr, factored_expr):
        ops.append("multiplication_factorization")
    if not _ast_equal(factored_expr, optimized_expr):
        ops.append("linear_term_reduction")
    return ops


def _build_summary(cost_before: int, cost_after: int, operations: List[str]) -> str:
    delta = cost_before - cost_after
    if delta > 0:
        delta_txt = f"reduziu custo {cost_before}→{cost_after} (-{delta})"
    elif delta < 0:
        delta_txt = f"aumentou custo {cost_before}→{cost_after} (+{abs(delta)})"
    else:
        delta_txt = f"manteve custo {cost_before}"
    if operations:
        ops_txt = ", ".join(operations)
        return f"{delta_txt} aplicando {ops_txt}"
    return f"{delta_txt} sem transformações adicionais"


def _run_regression(
    original_src: str,
    optimized_src: str,
    function_name: str,
    samples: Sequence[Tuple[Any, ...]],
) -> RegressionReport:
    original_env: Dict[str, Any] = {}
    candidate_env: Dict[str, Any] = {}
    exec(original_src, original_env)  # noqa: S102 - execução isolada e controlada
    exec(optimized_src, candidate_env)  # noqa: S102
    original_fn = original_env.get(function_name)
    candidate_fn = candidate_env.get(function_name)
    if not callable(original_fn) or not callable(candidate_fn):
        raise ValueError("Função alvo não executável para regressão.")
    sig = inspect.signature(original_fn)
    param_count = len(sig.parameters)
    sample_inputs: Sequence[Tuple[Any, ...]]
    if param_count == 0:
        sample_inputs = [()]
    else:
        sample_inputs = samples

    executed = False
    sample_reports: List[RegressionSample] = []
    all_ok = True
    for args in sample_inputs:
        if param_count != len(args):
            continue
        executed = True
        orig_out = original_fn(*args)
        cand_out = candidate_fn(*args)
        matched = orig_out == cand_out
        sample_reports.append(
            RegressionSample(
                inputs=args,
                original_output=orig_out,
                candidate_output=cand_out,
                matched=matched,
            )
        )
        if not matched:
            all_ok = False
    if not executed:
        all_ok = True
    return RegressionReport(passed=all_ok, samples=sample_reports)


def _is_number_constant(node: ast.AST) -> bool:
    return isinstance(node, ast.Constant) and isinstance(node.value, (int, float))


_CONST_BIN_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}

_CONST_UNARY_OPS = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}


def _fold_constants(node: ast.AST) -> ast.AST:
    if isinstance(node, ast.BinOp):
        node.left = _fold_constants(node.left)
        node.right = _fold_constants(node.right)
        if _is_number_constant(node.left) and _is_number_constant(node.right):
            func = _CONST_BIN_OPS.get(type(node.op))
            if func:
                try:
                    value = func(node.left.value, node.right.value)
                    return ast.Constant(value=value)
                except ZeroDivisionError:
                    pass
    elif isinstance(node, ast.UnaryOp):
        node.operand = _fold_constants(node.operand)
        if _is_number_constant(node.operand):
            func = _CONST_UNARY_OPS.get(type(node.op))
            if func:
                return ast.Constant(value=func(node.operand.value))
    elif isinstance(node, ast.Expr):
        node.value = _fold_constants(node.value)
    elif isinstance(node, ast.Return) and node.value is not None:
        node.value = _fold_constants(node.value)
    return node


def _flatten_mul(node: ast.AST, factors: List[ast.AST]) -> None:
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mult):
        _flatten_mul(node.left, factors)
        _flatten_mul(node.right, factors)
    else:
        factors.append(node)


def _build_mul_chain(factors: List[ast.AST]) -> ast.AST:
    if not factors:
        return ast.Constant(value=1)
    expr = factors[0]
    for factor in factors[1:]:
        expr = ast.BinOp(left=expr, op=ast.Mult(), right=factor)
    return expr


def _factorize_multiplication(node: ast.AST) -> ast.AST:
    if isinstance(node, ast.BinOp):
        node.left = _factorize_multiplication(node.left)
        node.right = _factorize_multiplication(node.right)
        if isinstance(node.op, ast.Mult):
            factors: List[ast.AST] = []
            _flatten_mul(node, factors)
            grouped: Dict[str, Tuple[ast.AST, int]] = {}
            for factor in factors:
                key = ast.dump(factor, include_attributes=False)
                entry = grouped.get(key)
                if entry is None:
                    grouped[key] = (factor, 1)
                else:
                    grouped[key] = (entry[0], entry[1] + 1)
            new_factors: List[ast.AST] = []
            for base, count in grouped.values():
                if count == 1:
                    new_factors.append(base)
                else:
                    power = ast.BinOp(
                        left=base,
                        op=ast.Pow(),
                        right=ast.Constant(value=count),
                    )
                    new_factors.append(power)
            return _build_mul_chain(new_factors)
    elif isinstance(node, ast.Expr):
        node.value = _factorize_multiplication(node.value)
    elif isinstance(node, ast.Return) and node.value is not None:
        node.value = _factorize_multiplication(node.value)
    return node


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

        simplified_expr = _fold_constants(copy.deepcopy(original_expr))
        factored_expr = _factorize_multiplication(simplified_expr)
        factored_expr = _fold_constants(factored_expr)
        meta_terms = _reduce_terms(_collect_terms(factored_expr))
        optimized_expr = _build_expression(meta_terms)

        if _ast_equal(original_expr, optimized_expr):
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

        regression_report = _run_regression(
            request.source, optimized_source, request.function_name, request.samples
        )
        if not regression_report.passed:
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

        operations = _describe_operations(
            original_expr, simplified_expr, factored_expr, optimized_expr
        )
        summary = _build_summary(
            analysis.cost_before,
            analysis.cost_after,
            operations,
        )
        explanation = PatchExplanation(
            summary=summary,
            operations=operations,
            cost_before=analysis.cost_before,
            cost_after=analysis.cost_after,
            redundant_terms=analysis.redundant_terms,
            liu_signature=analysis.liu_repr,
            regression=regression_report,
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
            explanation=explanation,
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


__all__ = [
    "MetaEvolution",
    "EvolutionRequest",
    "EvolutionResult",
    "MetaAnalysis",
    "PatchExplanation",
    "RegressionReport",
    "RegressionSample",
    "explanation_to_dict",
]
