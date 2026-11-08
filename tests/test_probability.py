import math

import pytest

from lqie.quant import normal_cdf, normal_pdf, normal_quantile


def test_standard_normal_values():
    assert normal_pdf(0) == pytest.approx(1 / math.sqrt(2 * math.pi))
    assert normal_cdf(0) == pytest.approx(0.5)
    assert normal_quantile(0.975) == pytest.approx(1.959963984540054, rel=1e-12)


def test_shifted_scaled_normal():
    assert normal_cdf(12, mean=10, standard_deviation=2) == pytest.approx(0.8413447460685429)
    assert normal_quantile(0.5, mean=10, standard_deviation=2) == pytest.approx(10)


def test_normal_rejects_invalid_sigma_and_probability():
    with pytest.raises(ValueError, match="positive"):
        normal_pdf(0, standard_deviation=0)
    with pytest.raises(ValueError, match="strictly between"):
        normal_quantile(1.0)
