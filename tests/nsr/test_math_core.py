from nsr.math_core import MathInstruction, MathCoreResult, parse_math_phrase, evaluate_math_phrase


def test_parse_math_phrase_recognizes_sqrt():
    instruction = parse_math_phrase("Qual é a raiz de 9?")
    assert instruction is not None
    assert instruction.operation == "sqrt"
    assert instruction.expression == "SQRT(9)"
    assert instruction.operands == (9.0,)
    term = instruction.as_term()
    assert term.label == "SQRT"


def test_parse_math_phrase_sum_multiple_operands():
    instruction = parse_math_phrase("Some 2 e 3 e 5")
    assert instruction is not None
    assert instruction.operation == "sum"
    assert instruction.expression == "2+3+5"


def test_evaluate_math_phrase_returns_value():
    result = evaluate_math_phrase("qual é a diferença entre 10 e 4?")
    assert result is not None
    assert isinstance(result, MathCoreResult)
    assert result.value == 6.0
    assert result.instruction.operation == "difference"


def test_parse_math_phrase_requires_operands():
    assert parse_math_phrase("Some números") is None
