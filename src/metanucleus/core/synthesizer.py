"""
Motor de Síntese de Programas (Indução Simbólica).

Substitui a "aprendizagem" estatística por "descoberta" algorítmica.
Dado um conjunto de exemplos (Input/Output), este motor busca no espaço
de funções possíveis aquela que satisfaz a transformação.

Abordagem: Busca em Largura (BFS) sobre primitivas tipadas.
"""

from dataclasses import dataclass
from typing import List, Any, Callable, Tuple, Dict, Union
import math
import operator

# --- Definição da DSL (Domain Specific Language) ---

@dataclass(frozen=True)
class Primitive:
    name: str
    func: Callable
    arity: int  # Número de argumentos
    input_types: List[type]
    output_type: type

@dataclass(frozen=True)
class Program:
    source: str
    func: Callable
    
    def __repr__(self):
        return self.source

# Primitivas Matemáticas e de String
def _safe_div(a, b):
    return a / b if b != 0 else 1

PRIMITIVES = [
    # Matemática Básica
    Primitive("add", operator.add, 2, [float, float], float),
    Primitive("sub", operator.sub, 2, [float, float], float),
    Primitive("mul", operator.mul, 2, [float, float], float),
    # Primitive("div", _safe_div, 2, [float, float], float), # Divisão explode busca rápido, deixar desativado por enquanto
    Primitive("neg", operator.neg, 1, [float], float),
    Primitive("sqr", lambda x: x*x, 1, [float], float),
    
    # Manipulação de String
    Primitive("upper", str.upper, 1, [str], str),
    Primitive("lower", str.lower, 1, [str], str),
    Primitive("rev", lambda x: x[::-1], 1, [str], str),
    Primitive("len", lambda x: float(len(x)), 1, [str], float),
    Primitive("first", lambda x: x[0] if x else "", 1, [str], str),
    Primitive("last", lambda x: x[-1] if x else "", 1, [str], str),
    Primitive("concat", operator.add, 2, [str, str], str),
]

class SymbolicSynthesizer:
    def __init__(self, max_depth: int = 3):
        self.max_depth = max_depth
        self.primitives = PRIMITIVES

    def synthesize(self, examples: List[Tuple[Any, Any]]) -> Union[Program, None]:
        """
        Busca um programa P tal que P(in) == out para todo exemplo.
        """
        if not examples:
            return None
        
        # Inferir tipos de entrada e saída
        in_sample = examples[0][0]
        out_sample = examples[0][1]
        
        # Normalização de tipos (int -> float para simplificar matemática)
        input_type = float if isinstance(in_sample, (int, float)) else str
        output_type = float if isinstance(out_sample, (int, float)) else str
        
        # Estado inicial da busca: (Código, Função, Tipo)
        # Começamos com a identidade (variável x)
        # Representação: (source_string, lambda_function, return_type)
        frontier: List[Tuple[str, Callable, type]] = [
            ("x", lambda x: x, input_type)
        ]
        
        # Constantes úteis para injetar
        if input_type == float:
            frontier.append(("1.0", lambda x: 1.0, float))
            frontier.append(("2.0", lambda x: 2.0, float))
        if input_type == str:
            frontier.append(("' '", lambda x: " ", str))
        
        # Loop de busca (BFS limitado por profundidade/tamanho)
        # Para evitar loop infinito, limitamos o número de programas explorados
        MAX_PROGRAMS = 5000
        explored_count = 0
        
        while frontier and explored_count < MAX_PROGRAMS:
            current_source, current_func, current_type = frontier.pop(0)
            
            # Verifica se resolve
            if current_type == output_type:
                if self._verify(current_func, examples):
                    return Program(current_source, current_func)
            
            explored_count += 1
            
            # Se o programa já está muito complexo, não expande
            # Heurística simples: profundidade aproximada pelo tamanho da string
            if current_source.count("(") > self.max_depth:
                continue

            # Expansão: Tentar aplicar primitivas sobre o programa atual
            for prim in self.primitives:
                # Unary ops
                if prim.arity == 1 and prim.input_types[0] == current_type:
                    new_source = f"{prim.name}({current_source})"
                    # Closure para capturar primitivas corretamente
                    new_func = self._make_unary(prim.func, current_func)
                    frontier.append((new_source, new_func, prim.output_type))
                
                # Binary ops (Simplificado: tenta combinar com ele mesmo ou constantes)
                # Busca completa binária é O(N^2), aqui fazemos uma versão "greedy"
                # combinando apenas com o input original 'x' para não explodir.
                if prim.arity == 2:
                    if prim.input_types[0] == current_type and prim.input_types[1] == input_type:
                        # Op(Current, Input)
                        new_source = f"{prim.name}({current_source}, x)"
                        new_func = self._make_binary_right_x(prim.func, current_func)
                        frontier.append((new_source, new_func, prim.output_type))
                    
                    if prim.input_types[0] == input_type and prim.input_types[1] == current_type:
                        # Op(Input, Current)
                        new_source = f"{prim.name}(x, {current_source})"
                        new_func = self._make_binary_left_x(prim.func, current_func)
                        frontier.append((new_source, new_func, prim.output_type))

        return None

    def _verify(self, func: Callable, examples: List[Tuple[Any, Any]]) -> bool:
        try:
            for inp, expected in examples:
                res = func(inp)
                # Comparação com tolerância para float
                if isinstance(expected, float):
                    if abs(res - expected) > 1e-5:
                        return False
                elif res != expected:
                    return False
            return True
        except Exception:
            return False

    # Helpers para criar closures limpas
    def _make_unary(self, prim_func, inner_func):
        return lambda x: prim_func(inner_func(x))

    def _make_binary_right_x(self, prim_func, inner_func):
        # prim(inner(x), x)
        return lambda x: prim_func(inner_func(x), x)

    def _make_binary_left_x(self, prim_func, inner_func):
        # prim(x, inner(x))
        return lambda x: prim_func(x, inner_func(x))

# Instância global
SYNTHESIZER = SymbolicSynthesizer()
