from nsr.regression_engine import solve_linear_regression


def test_simple_regression_two_features():
    payload = {
        "features": ["x1", "x2"],
        "target": "y",
        "data": [
            {"x1": 1, "x2": 1, "y": 3},
            {"x1": 2, "x2": 0, "y": 2},
            {"x1": 0, "x2": 3, "y": 6},
        ],
    }
    result = solve_linear_regression(payload)
    assert result.intercept is not None
    assert len(result.coefficients) == 2
    coeff_map = dict(result.coefficients)
    assert round(coeff_map["x1"], 3) == 1.0
    assert round(coeff_map["x2"], 3) == 2.0
    assert result.sample_size == 3
    assert 0 <= result.r_squared <= 1


def test_regression_without_intercept():
    payload = {
        "features": ["time"],
        "target": "value",
        "intercept": False,
        "data": [
            {"time": 1, "value": 2},
            {"time": 2, "value": 4},
            {"time": 3, "value": 6},
        ],
    }
    result = solve_linear_regression(payload)
    assert result.intercept is None
    coeff = dict(result.coefficients)["time"]
    assert round(coeff, 4) == 2.0
    assert result.mse == 0.0
