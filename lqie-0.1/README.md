# LQIE 0.1 — Lionare Quantitative Intelligence Engine

LQIE is a standalone numerical engine for Lionare. It does not generate text,
write code, fetch market data, or make investment recommendations.

## 0.1 scope

- Exact decimal-based market capitalization and enterprise value calculations.
- Simple and logarithmic historical returns.
- Annualized historical sample volatility.
- Historical maximum drawdown.
- Input validation and automated tests.

## Enterprise value convention

`EV = market_cap + total_debt + preferred_equity + minority_interest - cash_and_equivalents`

All money inputs must use the same currency and units. Shares and share price
must use compatible units. This is a base convention; production valuation
policies may add other adjustments such as leases, pension deficits, or
non-operating investments.

## Install in WSL

From the project directory:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[dev]'
pytest
```

## Quick valuation check

```bash
python - <<'PY'
from lqie.finance import calculate_valuation

result = calculate_valuation(
    shares_outstanding=100_000_000,
    share_price=50,
    total_debt=1_000_000_000,
    cash_and_equivalents=500_000_000,
)
print("Market cap:", result.market_cap)
print("Net debt and claims:", result.net_debt_and_claims)
print("Enterprise value:", result.enterprise_value)
PY
```

Expected values: market cap `$5,000,000,000`, net debt `$500,000,000`, EV
`$5,500,000,000`.

## Design boundary

- Deterministic arithmetic belongs here, not in an LLM.
- Neural forecasting models will be a separate package/module and will return
  predictions with uncertainty, model version, and data timestamp.
- All market data must retain source, event time, ingestion time, units,
  currency, and licensing metadata before it is used for research or training.
- No model is accepted without out-of-sample evaluation and reproducible tests.
