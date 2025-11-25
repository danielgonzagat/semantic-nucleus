from nsr.bayes_engine import BayesNetwork


def build_simple_network() -> BayesNetwork:
    network = BayesNetwork()
    network.add_variable("Rain", values=("yes", "no"))
    network.add_variable("Traffic", values=("jam", "clear"), parents=("Rain",))
    network.set_distribution("Rain", distribution={"yes": 0.2, "no": 0.8})
    network.set_distribution("Traffic", given={"Rain": "yes"}, distribution={"jam": 0.7, "clear": 0.3})
    network.set_distribution("Traffic", given={"Rain": "no"}, distribution={"jam": 0.1, "clear": 0.9})
    return network


def test_posterior_matches_prior_without_evidence():
    network = build_simple_network()
    posterior = network.posterior("Rain", {})
    assert posterior == {"yes": 0.2, "no": 0.8}


def test_posterior_with_evidence():
    network = build_simple_network()
    posterior = network.posterior("Traffic", {"Rain": "yes"})
    assert posterior["jam"] == 0.7
    assert posterior["clear"] == 0.3
