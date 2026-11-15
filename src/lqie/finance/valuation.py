"""Exact decimal-based equity valuation primitives.

Enterprise value convention used here:
    EV = market capitalization + total debt + preferred equity
         + minority interest - cash and cash equivalents

This is a clearly stated base convention. Production integrations may need
additional adjustments (leases, pension deficits, investments, etc.) based
on the instrument, data provider, and valuation policy.
"""

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import TypeAlias

DecimalInput: TypeAlias = Decimal | int | float | str
_ZERO = Decimal("0")


def _decimal(value: DecimalInput, field_name: str) -> Decimal:
    """Convert a numeric input to Decimal without binary-float arithmetic."""
    if isinstance(value, bool):
        raise TypeError(f"{field_name} must be numeric, not bool")
    try:
        result = value if isinstance(value, Decimal) else Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ValueError(f"{field_name} must be a valid number") from exc
    if not result.is_finite():
        raise ValueError(f"{field_name} must be finite")
    return result


def _non_negative(value: DecimalInput, field_name: str) -> Decimal:
    result = _decimal(value, field_name)
    if result < _ZERO:
        raise ValueError(f"{field_name} cannot be negative")
    return result


@dataclass(frozen=True, slots=True)
class ValuationResult:
    """A reproducible enterprise valuation result, expressed in input currency."""

    market_cap: Decimal
    net_debt_and_claims: Decimal
    enterprise_value: Decimal


def calculate_valuation(
    *,
    shares_outstanding: DecimalInput,
    share_price: DecimalInput,
    total_debt: DecimalInput,
    cash_and_equivalents: DecimalInput,
    preferred_equity: DecimalInput = _ZERO,
    minority_interest: DecimalInput = _ZERO,
) -> ValuationResult:
    """Calculate market capitalization, net debt/claims, and enterprise value.

    All monetary inputs must use the same currency and units. Shares and
    per-share price must use compatible units. The function does not fetch
    data, infer missing values, or apply corporate-action adjustments.
    """
    shares = _non_negative(shares_outstanding, "shares_outstanding")
    price = _non_negative(share_price, "share_price")
    debt = _non_negative(total_debt, "total_debt")
    cash = _non_negative(cash_and_equivalents, "cash_and_equivalents")
    preferred = _non_negative(preferred_equity, "preferred_equity")
    minority = _non_negative(minority_interest, "minority_interest")

    market_cap = shares * price
    net_debt_and_claims = debt + preferred + minority - cash
    enterprise_value = market_cap + net_debt_and_claims

    return ValuationResult(
        market_cap=market_cap,
        net_debt_and_claims=net_debt_and_claims,
        enterprise_value=enterprise_value,
    )
