from nsr.math_instinct import MathInstinct
from nsr.math_bridge import maybe_route_math
from nsr import SessionCtx, run_text


def test_math_instinct_evaluates_raw_expression():
    instinct = MathInstinct()
    reply = instinct.evaluate("2 + 2")
    assert reply is not None
    assert reply.text == "4"


def test_math_instinct_detects_spoken_expression():
    instinct = MathInstinct()
    reply = instinct.evaluate("Quanto é 3 * 5?")
    assert reply is not None
    assert reply.text == "15"


def test_math_bridge_preseeds_runtime():
    hook = maybe_route_math("3 + 3")
    assert hook is not None
    fields = dict(hook.answer_node.fields)
    assert fields["answer"].label == "6"
    answer, trace = run_text("4 * 4", SessionCtx())
    assert answer == "16"
    assert trace.steps[0].startswith("1:MATH[")


def test_math_instinct_functions():
    instinct = MathInstinct()
    assert instinct.evaluate("abs(-5)").text == "5"
    result = instinct.evaluate("sqrt(9)")
    assert result is not None
    assert result.text == "3"
