"""
Φ-CALCULUS v2 – Rigorous Recursive Descent Parser.

Replaces the naive linear scanner with a standard CS parser that respects
operator precedence (PEMDAS).

Grammar:
    Expression -> Term { ('+'|'-') Term }
    Term       -> Factor { ('*'|'/') Factor }
    Factor     -> '(' Expression ')' | Number
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Union
import re

@dataclass
class CalculusResult:
    kind: str
    result: Optional[float]
    expression_normalized: Optional[str]
    steps: List[str] = field(default_factory=list)
    confidence: float = 0.0

# --- Tokenizer ---

TOKEN_NUMBER = 'NUMBER'
TOKEN_PLUS   = 'PLUS'
TOKEN_MINUS  = 'MINUS'
TOKEN_MULT   = 'MULT'
TOKEN_DIV    = 'DIV'
TOKEN_LPAREN = 'LPAREN'
TOKEN_RPAREN = 'RPAREN'

@dataclass
class Token:
    type: str
    value: Union[float, str]

_WORD_TO_NUM = {
    "zero": 0, "um": 1, "uma": 1, "dois": 2, "duas": 2, "tres": 3, "três": 3,
    "quatro": 4, "cinco": 5, "seis": 6, "sete": 7, "oito": 8, "nove": 9, "dez": 10
}

_WORD_TO_OP = {
    "mais": TOKEN_PLUS, "somado": TOKEN_PLUS,
    "menos": TOKEN_MINUS, "subtraido": TOKEN_MINUS,
    "vezes": TOKEN_MULT, "multiplicado": TOKEN_MULT,
    "dividido": TOKEN_DIV,
    "x": TOKEN_MULT, "+": TOKEN_PLUS, "-": TOKEN_MINUS, "*": TOKEN_MULT, "/": TOKEN_DIV,
    "(": TOKEN_LPAREN, ")": TOKEN_RPAREN
}

def tokenize(text: str) -> List[Token]:
    tokens = []
    # Split by space, but handle punctuation around numbers if needed
    # For simplicity, we assume basic tokenization or split string
    raw_tokens = text.replace("(", " ( ").replace(")", " ) ").lower().split()
    
    for t in raw_tokens:
        if t in _WORD_TO_OP:
            tokens.append(Token(_WORD_TO_OP[t], t))
            continue
        
        if t in _WORD_TO_NUM:
            tokens.append(Token(TOKEN_NUMBER, float(_WORD_TO_NUM[t])))
            continue
            
        try:
            val = float(t.replace(",", "."))
            tokens.append(Token(TOKEN_NUMBER, val))
        except ValueError:
            pass # Ignore non-math words
            
    return tokens

# --- Parser & Evaluator ---

class Parser:
    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.pos = 0
        self.steps: List[str] = []
        self.normalized: List[str] = []

    def peek(self) -> Optional[Token]:
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return None

    def consume(self, type_name: str) -> Optional[Token]:
        t = self.peek()
        if t and t.type == type_name:
            self.pos += 1
            return t
        return None

    def parse_expression(self) -> float:
        # Expression -> Term { ('+'|'-') Term }
        val = self.parse_term()
        
        while True:
            t = self.peek()
            if t and t.type == TOKEN_PLUS:
                self.consume(TOKEN_PLUS)
                self.normalized.append("+")
                rhs = self.parse_term()
                old_val = val
                val += rhs
                self.steps.append(f"Add: {old_val} + {rhs} = {val}")
            elif t and t.type == TOKEN_MINUS:
                self.consume(TOKEN_MINUS)
                self.normalized.append("-")
                rhs = self.parse_term()
                old_val = val
                val -= rhs
                self.steps.append(f"Sub: {old_val} - {rhs} = {val}")
            else:
                break
        return val

    def parse_term(self) -> float:
        # Term -> Factor { ('*'|'/') Factor }
        val = self.parse_factor()
        
        while True:
            t = self.peek()
            if t and t.type == TOKEN_MULT:
                self.consume(TOKEN_MULT)
                self.normalized.append("*")
                rhs = self.parse_factor()
                old_val = val
                val *= rhs
                self.steps.append(f"Mult: {old_val} * {rhs} = {val}")
            elif t and t.type == TOKEN_DIV:
                self.consume(TOKEN_DIV)
                self.normalized.append("/")
                rhs = self.parse_factor()
                if rhs == 0:
                    raise ZeroDivisionError("Division by zero")
                old_val = val
                val /= rhs
                self.steps.append(f"Div: {old_val} / {rhs} = {val}")
            else:
                break
        return val

    def parse_factor(self) -> float:
        # Factor -> '(' Expression ')' | Number
        t = self.peek()
        if t and t.type == TOKEN_NUMBER:
            self.consume(TOKEN_NUMBER)
            self.normalized.append(str(t.value))
            return t.value
        elif t and t.type == TOKEN_LPAREN:
            self.consume(TOKEN_LPAREN)
            self.normalized.append("(")
            val = self.parse_expression()
            self.consume(TOKEN_RPAREN)
            self.normalized.append(")")
            return val
        else:
            raise ValueError("Expected number or parenthesis")

def phi_calculus(parse: Any) -> CalculusResult:
    # Extract text from semantic parse or use raw text if available
    # We'll assume 'parse' object has 'text' attribute or similar
    text_input = getattr(parse, "text", "") if hasattr(parse, "text") else str(parse)
    
    tokens = tokenize(text_input)
    
    if len(tokens) < 3: # Minimum "1 + 1"
        return CalculusResult("none", None, None, [], 0.0)

    parser = Parser(tokens)
    try:
        result = parser.parse_expression()
        expr_str = " ".join(parser.normalized)
        parser.steps.append(f"Final Result: {result}")
        
        return CalculusResult(
            kind="arithmetic",
            result=result,
            expression_normalized=expr_str,
            steps=parser.steps,
            confidence=1.0
        )
    except (ValueError, ZeroDivisionError) as e:
        return CalculusResult(
            kind="error",
            result=None,
            expression_normalized=None,
            steps=[str(e)],
            confidence=0.0
        )