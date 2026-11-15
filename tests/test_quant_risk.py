import pytest

from lqie.quant import historical_var_cvar, normal_var_cvar


def test_historical_var_cvar_known_sample():
    returns = [-0.10, 0.00, 0.05, -0.20, 0.10, 0.00, 0.02, -0.04, 0.03, 0.01]
    result = historical_var_cvar(returns, confidence=0.80)
    assert result.var == pytest.approx(0.10)
    assert result.cvar == pytest.approx(0.15)
    assert result.observations == 10
    assert result.method == "historical_higher_inclusive_tail"


def test_normal_var_cvar_known_values():
    result = normal_var_cvar(0.0, 0.01, confidence=0.95)
    assert result.var == pytest.approx(0.01644853626951472)
    assert result.cvar == pytest.approx(0.020627, rel=2e-4)
    assert result.observations == 0


def test_risk_rejects_invalid_inputs():
    with pytest.raises(ValueError, match="confidence"):
        historical_var_cvar([0.01, -0.01], confidence=1.0)
    with pytest.raises(ValueError, match="greater than -1"):
        historical_var_cvar([-1.0, 0.1])
    with pytest.raises(ValueError, match="cannot be negative"):
        normal_var_cvar(0.0, -0.1)
