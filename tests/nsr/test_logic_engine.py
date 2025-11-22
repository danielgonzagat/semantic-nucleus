from nsr.logic_engine import LogicEngine, LogicRule, negate, normalize_statement


def test_modus_ponens_single_premise():
    engine = LogicEngine()
    engine.add_fact("A")
    engine.add_rule(["A"], "B")
    new_facts = engine.infer()
    assert "B" in new_facts
    assert engine.facts["B"] is True


def test_modus_ponens_multiple_premises():
    engine = LogicEngine()
    engine.add_fact("P")
    engine.add_fact("Q")
    engine.add_rule(["P", "Q"], "R")
    engine.infer()
    assert engine.facts["R"]


def test_modus_tollens_derives_negated_premise():
    engine = LogicEngine()
    engine.add_rule(["RAINING"], "WET")
    engine.add_fact("NOT WET")
    engine.infer()
    assert "NOT RAINING" in engine.facts
    assert engine.facts["NOT RAINING"]


def test_contradictory_fact_raises():
    engine = LogicEngine()
    engine.add_fact("S")
    try:
        engine.add_fact("S", truth=False)
    except ValueError:
        pass
    else:
        raise AssertionError("Expected contradiction error")


def test_negate_helper_roundtrip():
    assert negate("A") == "NOT A"
    assert negate("NOT A") == "A"
    assert normalize_statement("  a  and b ") == "A AND B"
