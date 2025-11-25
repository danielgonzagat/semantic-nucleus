from nsr.markov_engine import MarkovModel


def build_chain():
    payload = {
        "states": ["Rain", "Dry"],
        "initial": {"Rain": 0.6, "Dry": 0.4},
        "transitions": [
            {"from": "Rain", "to": {"Rain": 0.7, "Dry": 0.3}},
            {"from": "Dry", "to": {"Rain": 0.2, "Dry": 0.8}},
        ],
        "emissions": [
            {"state": "Rain", "symbols": {"umbrella": 0.9, "no": 0.1}},
            {"state": "Dry", "symbols": {"umbrella": 0.2, "no": 0.8}},
        ],
    }
    return MarkovModel.from_payload(payload)


def test_forward_without_observations_is_transition_only():
    model = build_chain()
    final_distribution, history, likelihood = model.forward([])
    assert history == ()
    assert round(sum(final_distribution.values()), 6) == 1.0
    assert likelihood == 1.0


def test_forward_with_observations():
    model = build_chain()
    final_distribution, history, likelihood = model.forward(["umbrella", "umbrella"])
    assert len(history) == 2
    assert round(likelihood, 3) > 0
    rain_prob = final_distribution["Rain"]
    dry_prob = final_distribution["Dry"]
    assert round(rain_prob + dry_prob, 6) == 1.0
