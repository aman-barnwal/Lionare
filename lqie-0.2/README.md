# LQIE 0.2 — Lionare Quantitative Intelligence Engine

LQIE 0.2 extends the deterministic finance core with numerical statistics,
regression, probability, Monte Carlo simulation, and portfolio-tail-risk tools.
It is a numerical library, not an LLM and not a market-data provider.

## Scope

- **Retained from 0.1:** decimal-based valuation, simple/log returns,
  annualized historical volatility, and maximum drawdown.
- **Cross-asset statistics:** sample covariance and Pearson correlation matrices
  for aligned return series.
- **Regression:** ordinary least squares using `numpy.linalg.lstsq`, with
  coefficients, fit diagnostics, rank, fitted values, and residuals.
- **Probability:** normal PDF, CDF, and inverse CDF.
- **Monte Carlo:** seeded geometric Brownian motion (GBM) path simulation.
- **Risk:** historical and normal-parametric loss VaR/CVaR.

## Installation

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

## Verification

```bash
python -m compileall -q src/lqie
python -m pytest -v
python benchmarks/bench_quant.py --iterations 100 --batches 5
```

The benchmark is a local microbenchmark. Compare runs only under the same
hardware, operating system, Python/NumPy versions, and workload settings.

## Quick start

```python
from lqie.quant import (
    covariance_matrix,
    correlation_matrix,
    fit_ols,
    historical_var_cvar,
    normal_var_cvar,
    simulate_gbm_paths,
)

returns = {
    "ASSET_A": [0.01, -0.02, 0.015, 0.004],
    "ASSET_B": [0.008, -0.01, 0.012, 0.006],
}
print(covariance_matrix(returns))
print(correlation_matrix(returns))

ols = fit_ols(
    y=[3, 5, 7, 9],
    X=[1, 2, 3, 4],
    feature_names=["factor_1"],
)
print(ols.intercept, ols.coefficients, ols.r_squared)

print(historical_var_cvar(returns["ASSET_A"], confidence=0.95))
print(normal_var_cvar(mean_return=0.0005, volatility=0.02, confidence=0.95))

paths = simulate_gbm_paths(
    initial_price=100,
    annual_drift=0.07,
    annual_volatility=0.22,
    time_horizon_years=1,
    steps=252,
    n_paths=10_000,
    seed=42,
)
print(paths.shape)  # (10000, 253)
```

## Method conventions and limitations

1. Covariance is the **sample covariance** estimator (`ddof=1`). Correlation is
   Pearson correlation. Inputs must be aligned, finite simple-return series
   with equal observation counts. Missing observations are rejected rather
   than silently imputed.
2. OLS estimates minimize squared residuals. Rank deficiency is allowed and
   reported; a rank-deficient design can make individual coefficients
   non-identifiable. This module does not perform causal inference.
3. Normal-distribution functions assume a Gaussian distribution by definition.
4. Historical VaR uses NumPy's conservative `higher` quantile. Historical CVaR
   is the mean of all observed losses greater than or equal to that threshold.
   Tied boundary observations can make this inclusive tail larger than exactly
   `(1-confidence)` of the sample. Losses are `-returns`; positive VaR/CVaR
   represents a loss.
5. Parametric VaR/CVaR assumes normally distributed returns. Real financial
   returns may exhibit fat tails, skew, jumps, changing volatility, and
   dependence not captured by this model.
6. GBM assumes constant drift and volatility and lognormal price dynamics.
   It is a baseline simulation framework, **not a calibrated forecast**.
   Reproducibility is controlled by the random seed.
7. These routines calculate from supplied numeric inputs only. They do not
   fetch live or historical market data, adjust corporate actions, infer
   missing information, or recommend trades.

## Development policy

Every quantitative module should include correctness tests, invalid-input and
edge-case tests, numerical-stability checks where relevant, and reproducible
benchmarks. Predictive models will additionally require walk-forward,
out-of-sample, calibration, and transaction-cost-aware evaluation before use.
