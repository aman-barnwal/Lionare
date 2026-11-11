import pytest

from lqie.models.fundamental_trend import forecast_annual_metric


def test_positive_metric_forecast():
    rows = [
        {"year": 2021, "value": 100.0},
        {"year": 2022, "value": 110.0},
        {"year": 2023, "value": 121.0},
    ]

    result = forecast_annual_metric(rows, horizon=3)

    assert result["observations_used"] == 3
    assert len(result["forecasts"]) == 3
    assert result["forecasts"][0]["year"] == 2024
    assert result["forecasts"][0]["value"] > 121


def test_linear_forecast_for_negative_metric():
    rows = [
        {"year": 2021, "value": -10.0},
        {"year": 2022, "value": 5.0},
        {"year": 2023, "value": 20.0},
    ]

    result = forecast_annual_metric(rows)

    assert result["method"] == "Linear least-squares trend"
    assert len(result["forecasts"]) == 3


def test_minimum_history_required():
    with pytest.raises(ValueError):
        forecast_annual_metric([
            {"year": 2023, "value": 10.0},
            {"year": 2024, "value": 20.0},
        ])


def test_horizon_validation():
    with pytest.raises(ValueError):
        forecast_annual_metric(
            [{"year": 2021, "value": 1},
             {"year": 2022, "value": 2},
             {"year": 2023, "value": 3}],
            horizon=10,
        )
