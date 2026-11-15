import math

import pytest

from lqie.quant import correlation_matrix, covariance_matrix


def test_covariance_matrix_known_sample():
    result = covariance_matrix({"A": [0.0, 0.1, 0.2], "B": [0.0, 0.2, 0.4]})
    assert result.assets == ("A", "B")
    assert result.observations == 3
    assert result.values[0][0] == pytest.approx(0.01)
    assert result.values[0][1] == pytest.approx(0.02)
    assert result.values[1][1] == pytest.approx(0.04)


def test_correlation_perfect_positive_and_negative():
    positive = correlation_matrix({"A": [1, 2, 3], "B": [2, 4, 6]})
    negative = correlation_matrix({"A": [1, 2, 3], "C": [3, 2, 1]})
    assert positive.values[0][1] == pytest.approx(1.0)
    assert negative.values[0][1] == pytest.approx(-1.0)


def test_matrix_requires_aligned_series():
    with pytest.raises(ValueError, match="equal lengths"):
        covariance_matrix({"A": [0.1, 0.2], "B": [0.1, 0.2, 0.3]})


def test_correlation_rejects_zero_variance():
    with pytest.raises(ValueError, match="zero variance"):
        correlation_matrix({"A": [0.1, 0.1, 0.1], "B": [0.0, 0.1, 0.2]})


def test_matrix_rejects_non_finite_data():
    with pytest.raises(ValueError, match="finite"):
        covariance_matrix({"A": [0.1, math.nan], "B": [0.2, 0.3]})
