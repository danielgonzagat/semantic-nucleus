from nsr.polynomial_engine import factor_polynomial


def test_factor_polynomial_simple():
    payload = {
        "variable": "x",
        "coefficients": [1, -3, 2],  # x^2 - 3x + 2 = (x-1)(x-2)
    }
    result = factor_polynomial(payload)
    assert result.degree == 2
    assert len(result.factors) >= 2
    roots = sorted(root for _, root in result.factors)
    assert roots == [1.0, 2.0]
    assert result.residual == 0.0


def test_factor_polynomial_with_zero_leading_coeffs():
    payload = {
        "coefficients": [0, 1, -4],  # x - 4
    }
    result = factor_polynomial(payload)
    assert result.degree == 1
    assert len(result.factors) == 1
    assert result.factors[0][1] == 4.0
