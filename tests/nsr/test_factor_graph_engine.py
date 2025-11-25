from nsr.factor_graph_engine import FactorGraph


def build_simple_graph():
    payload = {
        "variables": [
            {"name": "Rain", "values": ["yes", "no"]},
            {"name": "Sprinkler", "values": ["on", "off"]},
        ],
        "factors": [
            {
                "name": "Weather",
                "variables": ["Rain"],
                "table": [
                    {"assignment": {"Rain": "yes"}, "value": 0.2},
                    {"assignment": {"Rain": "no"}, "value": 0.8},
                ],
            },
            {
                "name": "SprinklerFactor",
                "variables": ["Rain", "Sprinkler"],
                "table": [
                    {"assignment": {"Rain": "yes", "Sprinkler": "on"}, "value": 0.1},
                    {"assignment": {"Rain": "yes", "Sprinkler": "off"}, "value": 0.9},
                    {"assignment": {"Rain": "no", "Sprinkler": "on"}, "value": 0.5},
                    {"assignment": {"Rain": "no", "Sprinkler": "off"}, "value": 0.5},
                ],
            },
        ],
    }
    return FactorGraph.from_payload(payload)


def test_factor_graph_belief_propagation():
    graph = build_simple_graph()
    marginals = graph.belief_propagation()
    assert "Rain" in marginals
    assert "Sprinkler" in marginals
    assert abs(sum(marginals["Rain"].values()) - 1.0) < 1e-6
    assert abs(sum(marginals["Sprinkler"].values()) - 1.0) < 1e-6
