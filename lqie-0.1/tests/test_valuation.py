from decimal import Decimal

import pytest

from lqie.finance.valuation import calculate_valuation


def test_market_cap_and_enterprise_value_case():
    result = calculate_valuation(
        shares_outstanding=100_000_000,
        share_price=50,
        total_debt=1_000_000_000,
        cash_and_equivalents=500_000_000,
    )
    assert result.market_cap == Decimal("5000000000")
    assert result.net_debt_and_claims == Decimal("500000000")
    assert result.enterprise_value == Decimal("5500000000")


def test_preferred_equity_and_minority_interest_are_included():
    result = calculate_valuation(
        shares_outstanding="10",
        share_price="12.50",
        total_debt="20",
        cash_and_equivalents="5",
        preferred_equity="3",
        minority_interest="2",
    )
    assert result.market_cap == Decimal("125.00")
    assert result.net_debt_and_claims == Decimal("20")
    assert result.enterprise_value == Decimal("145.00")


def test_net_cash_can_make_enterprise_value_below_market_cap():
    result = calculate_valuation(
        shares_outstanding=10,
        share_price=10,
        total_debt=5,
        cash_and_equivalents=30,
    )
    assert result.net_debt_and_claims == Decimal("-25")
    assert result.enterprise_value == Decimal("75")


@pytest.mark.parametrize(
    "field,value",
    [
        ("shares_outstanding", -1),
        ("share_price", -1),
        ("total_debt", -1),
        ("cash_and_equivalents", -1),
        ("preferred_equity", -1),
        ("minority_interest", -1),
        ("total_debt", "NaN"),
        ("cash_and_equivalents", "Infinity"),
    ],
)
def test_invalid_inputs_are_rejected(field, value):
    inputs = dict(
        shares_outstanding=10,
        share_price=10,
        total_debt=5,
        cash_and_equivalents=2,
    )
    inputs[field] = value
    with pytest.raises(ValueError):
        calculate_valuation(**inputs)


def test_boolean_input_is_rejected():
    with pytest.raises(TypeError):
        calculate_valuation(
            shares_outstanding=True,
            share_price=10,
            total_debt=5,
            cash_and_equivalents=2,
        )
