from nsr.logic_bridge import LogicBridgeResult, maybe_route_logic


def test_logic_bridge_fact_and_rule():
    fact_result = maybe_route_logic("Fact temperatura alta")
    assert fact_result is not None
    engine = fact_result.engine
    rule_result = maybe_route_logic("Se temperatura alta então alarme", engine=engine)
    assert rule_result is not None
    assert rule_result.action == "rule"
    assert rule_result.conclusion == "ALARME"
    query_result = maybe_route_logic("Query alarme", engine=engine)
    assert query_result.truth is True


def test_logic_bridge_multiple_premises_and_negation():
    engine = maybe_route_logic("Fact sensor a", None).engine
    maybe_route_logic("Fact sensor b", engine)
    rule = maybe_route_logic("If sensor a and sensor b then sistema ativo", engine)
    assert rule is not None
    query_active = maybe_route_logic("query sistema ativo", engine)
    assert query_active.truth is True
    neg_fact = maybe_route_logic("Fact nao alerta", engine)
    assert "NOT ALERTA" in neg_fact.engine.facts


def test_logic_bridge_returns_none_for_unknown_pattern():
    assert maybe_route_logic("Hello world") is None
