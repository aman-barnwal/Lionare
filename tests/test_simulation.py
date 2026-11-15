import numpy as np
import pytest

from lqie.quant import simulate_gbm_paths


def test_gbm_shape_and_initial_price():
    paths = simulate_gbm_paths(
        initial_price=100, annual_drift=0.05, annual_volatility=0.2,
        time_horizon_years=1, steps=12, n_paths=100, seed=7,
    )
    assert paths.shape == (100, 13)
    assert np.all(paths[:, 0] == 100)
    assert np.all(paths > 0)


def test_gbm_is_reproducible_with_seed():
    kwargs = dict(
        initial_price=100, annual_drift=0.05, annual_volatility=0.2,
        time_horizon_years=1, steps=12, n_paths=20, seed=42,
    )
    assert np.array_equal(simulate_gbm_paths(**kwargs), simulate_gbm_paths(**kwargs))


def test_gbm_zero_volatility_is_deterministic():
    paths = simulate_gbm_paths(
        initial_price=100, annual_drift=0.1, annual_volatility=0,
        time_horizon_years=1, steps=10, n_paths=3, seed=1,
    )
    assert paths[:, -1] == pytest.approx(np.array([100 * np.exp(0.1)] * 3))


def test_gbm_rejects_invalid_parameters():
    with pytest.raises(ValueError, match="positive"):
        simulate_gbm_paths(
            initial_price=0, annual_drift=0.1, annual_volatility=0.2,
            time_horizon_years=1,
        )
    with pytest.raises(ValueError, match="steps"):
        simulate_gbm_paths(
            initial_price=100, annual_drift=0.1, annual_volatility=0.2,
            time_horizon_years=1, steps=0,
        )
