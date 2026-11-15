import pytest

from lqie.finance.risk import max_drawdown


def test_max_drawdown():
    assert max_drawdown([100, 120, 90, 110, 80]) == pytest.approx(1 / 3)


def test_no_drawdown():
    assert max_drawdown([100, 105, 110]) == pytest.approx(0.0)


def test_drawdown_requires_valid_prices():
    with pytest.raises(ValueError):
        max_drawdown([100])
    with pytest.raises(ValueError):
        max_drawdown([100, -2])
