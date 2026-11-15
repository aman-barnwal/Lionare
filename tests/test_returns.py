import math

import pytest

from lqie.finance.returns import annualized_volatility, log_returns, simple_returns


def test_simple_returns():
    result = simple_returns([100, 110, 99])
    assert result == pytest.approx([0.10, -0.10])


def test_log_returns():
    result = log_returns([100, 110])
    assert result == pytest.approx([math.log(1.1)])


def test_annualized_volatility_uses_sample_standard_deviation():
    returns = [0.01, -0.01, 0.02, -0.02]
    expected = pytest.approx(__import__("statistics").stdev(returns) * math.sqrt(252))
    assert annualized_volatility(returns) == expected


def test_invalid_price_series_is_rejected():
    with pytest.raises(ValueError):
        simple_returns([100, 0])
    with pytest.raises(ValueError):
        log_returns([100])


def test_invalid_returns_are_rejected():
    with pytest.raises(ValueError):
        annualized_volatility([0.01])
    with pytest.raises(ValueError):
        annualized_volatility([-1.0, 0.1])
