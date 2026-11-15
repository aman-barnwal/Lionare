import pytest

from lqie.quant import fit_ols


def test_simple_ols_exact_line():
    result = fit_ols([3, 5, 7, 9], [1, 2, 3, 4], feature_names=["sales"])
    assert result.intercept == pytest.approx(1.0)
    assert result.coefficients == pytest.approx((2.0,))
    assert result.r_squared == pytest.approx(1.0)
    assert result.residual_standard_error == pytest.approx(0.0)
    assert result.rank == 2


def test_multiple_regression_exact_plane():
    X = [[0, 0], [1, 0], [0, 1], [1, 1], [2, 1]]
    y = [5, 7, 2, 4, 6]
    result = fit_ols(y, X, feature_names=["x1", "x2"])
    assert result.intercept == pytest.approx(5.0)
    assert result.coefficients == pytest.approx((2.0, -3.0))
    assert result.r_squared == pytest.approx(1.0)


def test_ols_without_intercept():
    result = fit_ols([2, 4, 6], [1, 2, 3], fit_intercept=False)
    assert result.intercept == 0.0
    assert result.coefficients == pytest.approx((2.0,))


def test_ols_rejects_bad_shapes():
    with pytest.raises(ValueError, match="shape"):
        fit_ols([1, 2, 3], [[1], [2]])


def test_ols_rejects_non_finite_features():
    with pytest.raises(ValueError, match="finite"):
        fit_ols([1, 2, 3], [1, float("inf"), 3])
