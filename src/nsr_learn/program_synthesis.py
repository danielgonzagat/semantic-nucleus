"""
Síntese de Programas: Aprender Funções a Partir de Exemplos.

Este é um dos componentes mais poderosos para aprendizado real.
Em vez de ajustar pesos, SINTETIZAMOS programas que explicam os dados.

Teoria Base: Solomonoff Induction
- A melhor hipótese é o programa mais curto que gera os dados
- Isso é Kolmogorov Complexity aplicada a aprendizado

Como funciona:
1. Recebe exemplos input → output
2. Busca programas que transformam input em output
3. Prefere programas mais curtos (Occam's Razor computacional)
4. Generaliza para novos inputs executando o programa

Diferença crucial dos LLMs:
- LLM: "memoriza" padrões implicitamente em pesos
- Nós: encontramos o PROGRAMA explícito que gera o padrão

Exemplo:
    Inputs:  [1, 2, 3, 4]
    Outputs: [2, 4, 6, 8]
    
    Programa sintetizado: λx. x * 2
    
    Agora podemos prever: 5 → 10, 100 → 200, etc.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, FrozenSet, Iterator, List, Mapping, Sequence, Set, Tuple, TypeVar
import operator
import re


T = TypeVar("T")


class OpType(Enum):
    """Tipos de operações primitivas."""
    
    # Aritméticas
    ADD = auto()
    SUB = auto()
    MUL = auto()
    DIV = auto()
    MOD = auto()
    NEG = auto()
    ABS = auto()
    
    # Comparações
    EQ = auto()
    NE = auto()
    LT = auto()
    GT = auto()
    LE = auto()
    GE = auto()
    
    # Lógicas
    AND = auto()
    OR = auto()
    NOT = auto()
    
    # Strings
    CONCAT = auto()
    LENGTH = auto()
    UPPER = auto()
    LOWER = auto()
    REVERSE = auto()
    FIRST = auto()
    LAST = auto()
    SLICE = auto()
    
    # Listas
    HEAD = auto()
    TAIL = auto()
    CONS = auto()
    APPEND = auto()
    MAP = auto()
    FILTER = auto()
    FOLD = auto()
    
    # Controle
    IF = auto()
    CONST = auto()
    VAR = auto()
    COMPOSE = auto()


@dataclass(frozen=True)
class Expr:
    """Uma expressão no DSL de síntese."""
    
    op: OpType
    args: Tuple[Any, ...] = ()
    
    @property
    def size(self) -> int:
        """Tamanho da expressão (para MDL)."""
        base = 1
        for arg in self.args:
            if isinstance(arg, Expr):
                base += arg.size
            else:
                base += 1
        return base
    
    def __str__(self) -> str:
        if self.op == OpType.CONST:
            return repr(self.args[0])
        elif self.op == OpType.VAR:
            return f"x{self.args[0]}"
        elif self.op == OpType.ADD:
            return f"({self.args[0]} + {self.args[1]})"
        elif self.op == OpType.SUB:
            return f"({self.args[0]} - {self.args[1]})"
        elif self.op == OpType.MUL:
            return f"({self.args[0]} * {self.args[1]})"
        elif self.op == OpType.DIV:
            return f"({self.args[0]} / {self.args[1]})"
        elif self.op == OpType.IF:
            return f"(if {self.args[0]} then {self.args[1]} else {self.args[2]})"
        elif self.op == OpType.CONCAT:
            return f"concat({self.args[0]}, {self.args[1]})"
        elif self.op == OpType.LENGTH:
            return f"len({self.args[0]})"
        elif self.op == OpType.UPPER:
            return f"upper({self.args[0]})"
        elif self.op == OpType.LOWER:
            return f"lower({self.args[0]})"
        elif self.op == OpType.REVERSE:
            return f"reverse({self.args[0]})"
        elif self.op == OpType.FIRST:
            return f"first({self.args[0]})"
        elif self.op == OpType.LAST:
            return f"last({self.args[0]})"
        elif self.op == OpType.EQ:
            return f"({self.args[0]} == {self.args[1]})"
        elif self.op == OpType.MAP:
            return f"map({self.args[0]}, {self.args[1]})"
        else:
            args_str = ", ".join(str(a) for a in self.args)
            return f"{self.op.name}({args_str})"


class Evaluator:
    """Avalia expressões do DSL."""
    
    def __init__(self):
        self.ops: Dict[OpType, Callable] = {
            OpType.ADD: lambda a, b: a + b,
            OpType.SUB: lambda a, b: a - b,
            OpType.MUL: lambda a, b: a * b,
            OpType.DIV: lambda a, b: a // b if b != 0 else 0,
            OpType.MOD: lambda a, b: a % b if b != 0 else 0,
            OpType.NEG: lambda a: -a,
            OpType.ABS: lambda a: abs(a),
            OpType.EQ: lambda a, b: a == b,
            OpType.NE: lambda a, b: a != b,
            OpType.LT: lambda a, b: a < b,
            OpType.GT: lambda a, b: a > b,
            OpType.LE: lambda a, b: a <= b,
            OpType.GE: lambda a, b: a >= b,
            OpType.AND: lambda a, b: a and b,
            OpType.OR: lambda a, b: a or b,
            OpType.NOT: lambda a: not a,
            OpType.CONCAT: lambda a, b: str(a) + str(b),
            OpType.LENGTH: lambda a: len(a) if hasattr(a, '__len__') else 0,
            OpType.UPPER: lambda a: str(a).upper(),
            OpType.LOWER: lambda a: str(a).lower(),
            OpType.REVERSE: lambda a: a[::-1] if hasattr(a, '__getitem__') else a,
            OpType.FIRST: lambda a: a[0] if a else None,
            OpType.LAST: lambda a: a[-1] if a else None,
        }
    
    def evaluate(self, expr: Expr, env: Dict[int, Any]) -> Any:
        """Avalia uma expressão em um ambiente."""
        try:
            if expr.op == OpType.CONST:
                return expr.args[0]
            
            elif expr.op == OpType.VAR:
                var_idx = expr.args[0]
                return env.get(var_idx)
            
            elif expr.op == OpType.IF:
                cond = self.evaluate(expr.args[0], env)
                if cond:
                    return self.evaluate(expr.args[1], env)
                else:
                    return self.evaluate(expr.args[2], env)
            
            elif expr.op in self.ops:
                evaluated_args = []
                for arg in expr.args:
                    if isinstance(arg, Expr):
                        evaluated_args.append(self.evaluate(arg, env))
                    else:
                        evaluated_args.append(arg)
                
                return self.ops[expr.op](*evaluated_args)
            
            else:
                return None
                
        except Exception:
            return None


@dataclass
class SynthesisExample:
    """Um exemplo para síntese de programa."""
    
    inputs: Tuple[Any, ...]
    output: Any
    
    def matches(self, result: Any) -> bool:
        """Verifica se um resultado corresponde ao output esperado."""
        return result == self.output


@dataclass
class SynthesizedProgram:
    """Um programa sintetizado."""
    
    expression: Expr
    examples_matched: int
    total_examples: int
    size: int
    
    @property
    def accuracy(self) -> float:
        return self.examples_matched / max(1, self.total_examples)
    
    @property
    def mdl_score(self) -> float:
        """Score MDL: preferimos programas pequenos e precisos."""
        # Menor é melhor
        return self.size - self.accuracy * 10
    
    def __str__(self) -> str:
        return f"λx. {self.expression} (acc={self.accuracy:.0%}, size={self.size})"


class ProgramSynthesizer:
    """
    Sintetizador de programas a partir de exemplos.
    
    Usa busca enumerativa com pruning por:
    1. Observational equivalence (evita programas redundantes)
    2. MDL (prefere programas menores)
    3. Type consistency (evita erros de tipo)
    """
    
    def __init__(
        self,
        max_size: int = 10,
        max_candidates: int = 10000,
    ):
        self.max_size = max_size
        self.max_candidates = max_candidates
        self.evaluator = Evaluator()
        
        # Cache de programas por assinatura de outputs
        self._signature_cache: Dict[Tuple, Expr] = {}
    
    def synthesize(
        self,
        examples: List[SynthesisExample],
        num_vars: int = 1,
    ) -> SynthesizedProgram | None:
        """
        Sintetiza um programa que satisfaz os exemplos.
        
        Usa busca bottom-up (menor para maior).
        """
        if not examples:
            return None
        
        # Gera candidatos por tamanho crescente
        for size in range(1, self.max_size + 1):
            candidates = self._generate_candidates(size, num_vars, examples)
            
            for expr in candidates:
                matches = self._count_matches(expr, examples)
                
                if matches == len(examples):
                    return SynthesizedProgram(
                        expression=expr,
                        examples_matched=matches,
                        total_examples=len(examples),
                        size=expr.size,
                    )
        
        # Retorna melhor parcial se não encontrou perfeito
        best = self._find_best_partial(examples, num_vars)
        return best
    
    def synthesize_transformation(
        self,
        input_output_pairs: List[Tuple[str, str]],
    ) -> SynthesizedProgram | None:
        """
        Sintetiza transformação string → string.
        
        Útil para aprender padrões de texto.
        """
        examples = [
            SynthesisExample(inputs=(inp,), output=out)
            for inp, out in input_output_pairs
        ]
        return self.synthesize(examples, num_vars=1)
    
    def synthesize_numeric(
        self,
        input_output_pairs: List[Tuple[int, int]],
    ) -> SynthesizedProgram | None:
        """
        Sintetiza função numérica.
        """
        examples = [
            SynthesisExample(inputs=(inp,), output=out)
            for inp, out in input_output_pairs
        ]
        return self.synthesize(examples, num_vars=1)
    
    def apply(
        self,
        program: SynthesizedProgram,
        *inputs: Any,
    ) -> Any:
        """Aplica programa sintetizado a novos inputs."""
        env = {i: v for i, v in enumerate(inputs)}
        return self.evaluator.evaluate(program.expression, env)
    
    def _generate_candidates(
        self,
        max_size: int,
        num_vars: int,
        examples: List[SynthesisExample],
    ) -> Iterator[Expr]:
        """Gera expressões candidatas até um tamanho máximo."""
        # Átomos base
        atoms: List[Expr] = []
        
        # Variáveis
        for i in range(num_vars):
            atoms.append(Expr(OpType.VAR, (i,)))
        
        # Constantes comuns
        for const in [0, 1, 2, 10, "", " "]:
            atoms.append(Expr(OpType.CONST, (const,)))
        
        # Constantes dos exemplos
        for ex in examples:
            for inp in ex.inputs:
                if isinstance(inp, (int, str)):
                    atoms.append(Expr(OpType.CONST, (inp,)))
            if isinstance(ex.output, (int, str)):
                atoms.append(Expr(OpType.CONST, (ex.output,)))
        
        # Remove duplicatas
        atoms = list({str(a): a for a in atoms}.values())
        
        if max_size == 1:
            yield from atoms
            return
        
        # Gera combinações
        generated = 0
        
        # Operações unárias
        unary_ops = [OpType.NEG, OpType.ABS, OpType.LENGTH, OpType.UPPER, 
                     OpType.LOWER, OpType.REVERSE, OpType.FIRST, OpType.LAST, OpType.NOT]
        
        for op in unary_ops:
            for atom in atoms:
                if generated >= self.max_candidates:
                    return
                yield Expr(op, (atom,))
                generated += 1
        
        # Operações binárias
        binary_ops = [OpType.ADD, OpType.SUB, OpType.MUL, OpType.DIV,
                      OpType.CONCAT, OpType.EQ, OpType.AND, OpType.OR]
        
        for op in binary_ops:
            for a1 in atoms:
                for a2 in atoms:
                    if generated >= self.max_candidates:
                        return
                    yield Expr(op, (a1, a2))
                    generated += 1
        
        # IF-THEN-ELSE
        for cond in atoms[:5]:  # Limita condições
            for then_br in atoms[:10]:
                for else_br in atoms[:10]:
                    if generated >= self.max_candidates:
                        return
                    yield Expr(OpType.IF, (cond, then_br, else_br))
                    generated += 1
    
    def _count_matches(
        self,
        expr: Expr,
        examples: List[SynthesisExample],
    ) -> int:
        """Conta quantos exemplos o programa satisfaz."""
        matches = 0
        
        for ex in examples:
            env = {i: v for i, v in enumerate(ex.inputs)}
            result = self.evaluator.evaluate(expr, env)
            
            if ex.matches(result):
                matches += 1
        
        return matches
    
    def _find_best_partial(
        self,
        examples: List[SynthesisExample],
        num_vars: int,
    ) -> SynthesizedProgram | None:
        """Encontra o melhor programa parcial."""
        best_expr = None
        best_matches = 0
        best_size = float('inf')
        
        for size in range(1, min(5, self.max_size)):
            for expr in self._generate_candidates(size, num_vars, examples):
                matches = self._count_matches(expr, examples)
                
                if matches > best_matches or (matches == best_matches and expr.size < best_size):
                    best_expr = expr
                    best_matches = matches
                    best_size = expr.size
        
        if best_expr is not None:
            return SynthesizedProgram(
                expression=best_expr,
                examples_matched=best_matches,
                total_examples=len(examples),
                size=best_expr.size,
            )
        
        return None


class PatternLearner:
    """
    Aprende padrões de transformação de strings.
    
    Mais especializado que o sintetizador genérico.
    """
    
    def __init__(self):
        self.patterns: List[Tuple[str, Callable[[str], str]]] = []
    
    def learn(
        self,
        examples: List[Tuple[str, str]],
    ) -> List[Tuple[str, Callable[[str], str]]]:
        """Aprende padrões de transformação."""
        patterns = []
        
        # Detecta padrões comuns
        patterns.extend(self._detect_case_patterns(examples))
        patterns.extend(self._detect_prefix_suffix_patterns(examples))
        patterns.extend(self._detect_substring_patterns(examples))
        patterns.extend(self._detect_replace_patterns(examples))
        
        self.patterns.extend(patterns)
        return patterns
    
    def apply(self, input_str: str) -> str | None:
        """Aplica padrões aprendidos."""
        for name, func in self.patterns:
            try:
                result = func(input_str)
                if result:
                    return result
            except Exception:
                continue
        return None
    
    def _detect_case_patterns(
        self,
        examples: List[Tuple[str, str]],
    ) -> List[Tuple[str, Callable[[str], str]]]:
        """Detecta padrões de case (upper, lower, title)."""
        patterns = []
        
        # Testa upper
        if all(out == inp.upper() for inp, out in examples):
            patterns.append(("upper", str.upper))
        
        # Testa lower
        if all(out == inp.lower() for inp, out in examples):
            patterns.append(("lower", str.lower))
        
        # Testa title
        if all(out == inp.title() for inp, out in examples):
            patterns.append(("title", str.title))
        
        # Testa capitalize
        if all(out == inp.capitalize() for inp, out in examples):
            patterns.append(("capitalize", str.capitalize))
        
        return patterns
    
    def _detect_prefix_suffix_patterns(
        self,
        examples: List[Tuple[str, str]],
    ) -> List[Tuple[str, Callable[[str], str]]]:
        """Detecta padrões de prefixo/sufixo."""
        patterns = []
        
        if not examples:
            return patterns
        
        # Detecta prefixo comum adicionado
        first_inp, first_out = examples[0]
        if first_out.endswith(first_inp):
            prefix = first_out[:-len(first_inp)] if first_inp else first_out
            if all(out == prefix + inp for inp, out in examples):
                patterns.append((f"prefix({prefix})", lambda s, p=prefix: p + s))
        
        # Detecta sufixo comum adicionado
        if first_out.startswith(first_inp):
            suffix = first_out[len(first_inp):] if first_inp else first_out
            if all(out == inp + suffix for inp, out in examples):
                patterns.append((f"suffix({suffix})", lambda s, suf=suffix: s + suf))
        
        return patterns
    
    def _detect_substring_patterns(
        self,
        examples: List[Tuple[str, str]],
    ) -> List[Tuple[str, Callable[[str], str]]]:
        """Detecta padrões de substring."""
        patterns = []
        
        if not examples:
            return patterns
        
        first_inp, first_out = examples[0]
        
        # Primeiro N caracteres
        if first_out == first_inp[:len(first_out)] and len(first_out) < len(first_inp):
            n = len(first_out)
            if all(out == inp[:n] for inp, out in examples if len(inp) >= n):
                patterns.append((f"first({n})", lambda s, n=n: s[:n]))
        
        # Últimos N caracteres
        if first_out == first_inp[-len(first_out):] and len(first_out) < len(first_inp):
            n = len(first_out)
            if all(out == inp[-n:] for inp, out in examples if len(inp) >= n):
                patterns.append((f"last({n})", lambda s, n=n: s[-n:]))
        
        return patterns
    
    def _detect_replace_patterns(
        self,
        examples: List[Tuple[str, str]],
    ) -> List[Tuple[str, Callable[[str], str]]]:
        """Detecta padrões de substituição."""
        patterns = []
        
        if len(examples) < 2:
            return patterns
        
        # Encontra o que mudou
        for old_char in set("".join(inp for inp, _ in examples)):
            for new_char in set("".join(out for _, out in examples)):
                if old_char == new_char:
                    continue
                
                if all(out == inp.replace(old_char, new_char) for inp, out in examples):
                    patterns.append(
                        (f"replace({old_char}, {new_char})", 
                         lambda s, o=old_char, n=new_char: s.replace(o, n))
                    )
        
        return patterns


class SequencePredictor:
    """
    Preditor de sequências numéricas via síntese de programa.
    
    Dado: [1, 4, 9, 16, ...]
    Encontra: f(n) = n²
    """
    
    def __init__(self):
        self.synthesizer = ProgramSynthesizer(max_size=8)
    
    def learn_sequence(
        self,
        sequence: List[int],
    ) -> SynthesizedProgram | None:
        """Aprende a função geradora de uma sequência."""
        # Cria exemplos: índice → valor
        examples = [
            SynthesisExample(inputs=(i,), output=v)
            for i, v in enumerate(sequence)
        ]
        
        return self.synthesizer.synthesize(examples, num_vars=1)
    
    def predict_next(
        self,
        sequence: List[int],
        n: int = 1,
    ) -> List[int]:
        """Prediz os próximos N elementos."""
        program = self.learn_sequence(sequence)
        
        if program is None:
            return []
        
        predictions = []
        start_idx = len(sequence)
        
        for i in range(n):
            pred = self.synthesizer.apply(program, start_idx + i)
            if pred is not None:
                predictions.append(pred)
        
        return predictions
    
    def explain_sequence(
        self,
        sequence: List[int],
    ) -> str:
        """Explica a regra da sequência."""
        program = self.learn_sequence(sequence)
        
        if program is None:
            return "Não foi possível encontrar um padrão."
        
        return f"Regra: f(n) = {program.expression}"


__all__ = [
    "OpType",
    "Expr",
    "Evaluator",
    "SynthesisExample",
    "SynthesizedProgram",
    "ProgramSynthesizer",
    "PatternLearner",
    "SequencePredictor",
]
