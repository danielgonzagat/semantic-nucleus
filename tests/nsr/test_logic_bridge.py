from nsr.logic_bridge import LogicBridgeResult, maybe_route_logic
from nsr import run_text, SessionCtx


def test_logic_bridge_fact_and_rule():
    fact_result = maybe_route_logic("Fact temperatura alta")
    assert fact_result is not None
    engine = fact_result.result.engine
    rule_result = maybe_route_logic("Se temperatura alta então alarme", engine=engine)
    assert rule_result is not None
    assert rule_result.result.action == "rule"
    assert rule_result.result.conclusion == "ALARME"
    query_result = maybe_route_logic("Query alarme", engine=engine)
    assert query_result.result.truth is True


def test_logic_bridge_multiple_premises_and_negation():
    hook_a = maybe_route_logic("Fact sensor a", None)
    assert hook_a is not None
    engine = hook_a.result.engine
    maybe_route_logic("Fact sensor b", engine)
    rule = maybe_route_logic("If sensor a and sensor b then sistema ativo", engine)
    assert rule is not None
    query_active = maybe_route_logic("query sistema ativo", engine)
    assert query_active.result.truth is True
    neg_fact = maybe_route_logic("Fact nao alerta", engine)
    assert "NOT ALERTA" in neg_fact.result.engine.facts


def test_logic_bridge_returns_none_for_unknown_pattern():
    assert maybe_route_logic("Hello world") is None


def test_run_text_handles_logic_commands():
    session = SessionCtx()
    answer, trace = run_text("Fact sensor ativo", session)
    assert answer.startswith("FACT OK")
    answer, trace = run_text("Query sensor ativo", session)
    assert answer.startswith("TRUE:")
