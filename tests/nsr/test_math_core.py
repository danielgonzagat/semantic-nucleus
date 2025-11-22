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


def test_parse_math_phrase_with_number_words():
    instruction = parse_math_phrase("qual é a raiz de nove?")
    assert instruction is not None
    assert instruction.operands == (9.0,)


def test_parse_power_operation():
    instruction = parse_math_phrase("2 elevado a 3")
    assert instruction is not None
    assert instruction.operation == "power"
    assert instruction.expression == "2**3"


def test_parse_percent_operation():
    instruction = parse_math_phrase("quanto é 20 por cento de 50?")
    assert instruction is not None
    assert instruction.operation == "percent"
    assert instruction.expression == "(20*50)/100"
