# LQIE — Lionare Quantitative Intelligence Engine

**Version:** 0.3.0  
**Project:** Lionare Financial Intelligence Platform  
**Status:** Active Research and Development

## Overview

LQIE (Lionare Quantitative Intelligence Engine) is an independent quantitative mathematics and numerical intelligence engine being developed for the Lionare Financial Intelligence Platform.

Its objective is to provide reliable financial calculations, statistical analysis, quantitative modelling, risk analytics and machine-learning-based financial forecasting.

LQIE is designed to operate independently of language models. Its mathematical and predictive outputs are numerical, structured and independently testable.

## Core Components

### 1. Financial Mathematics
- Market capitalization
- Enterprise valuation
- Net debt and financial claims
- Simple and logarithmic returns
- Annualized volatility
- Maximum drawdown

### 2. Quantitative Mathematics
- Covariance matrices
- Correlation matrices
- Ordinary least squares regression
- Probability distributions
- Monte Carlo simulation
- Geometric Brownian Motion
- Value at Risk (VaR)
- Conditional Value at Risk (CVaR)

### 3. Neural Intelligence
- PyTorch-based neural network architecture
- Multi-Horizon Multilayer Perceptron (MLP)
- Numerical financial feature inputs
- 1-day, 5-day and 20-day forecasting outputs
- GPU-accelerated training support

### 4. Financial Data Integration
- OpenBB integration
- CBOE historical OHLCV data retrieval
- Canonical financial data schema
- Data normalization and validation
- Historical dataset ingestion

### 5. Testing and Benchmarking
- Automated mathematical tests
- Neural network tests
- Data adapter tests
- Numerical validation
- Performance benchmarks
- Reproducible evaluation

## Technology Stack

| Technology | Purpose |
|---|---|
| Python | Core development |
| PyTorch | Neural network development |
| NumPy | Numerical computation |
| SciPy | Scientific computing |
| Scikit-learn | Statistical and machine-learning baselines |
| Polars | Financial data processing |
| OpenBB | Financial data integration |
| pytest | Automated testing |
| CUDA | GPU acceleration |

## Project Structure

```text
lqie-0.3/
│
├── src/
│   └── lqie/
│       ├── __init__.py
│       ├── finance/
│       ├── models/
│       │   ├── __init__.py
│       │   └── forecast_mlp.py
│       └── data/
│           ├── __init__.py
│           ├── schema.py
│           └── providers/
│               ├── __init__.py
│               └── openbb_cboe.py
│
├── tests/
│   ├── test_forecast_mlp.py
│   ├── test_openbb_adapter.py
│   ├── test_matrix.py
│   ├── test_probability.py
│   ├── test_quant_risk.py
│   ├── test_regression.py
│   ├── test_returns.py
│   ├── test_risk.py
│   ├── test_simulation.py
│   └── test_valuation.py
│
├── benchmarks/
│   ├── bench_quant.py
│   └── bench_data.py
│
├── pyproject.toml
├── README.md
└── .gitignore
```

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/aman-barnwal/Lionare.git
cd Lionare
```

For the dedicated LQIE development branch:

```bash
git switch dev/lqie-0.3
```

### 2. Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Core Dependencies

```bash
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

### 4. Install PyTorch

Install the appropriate PyTorch build for your system.

For the CUDA 13.0 development environment used during LQIE development:

```bash
python -m pip install torch \
  --index-url https://download.pytorch.org/whl/cu130
```

Install additional data-science dependencies:

```bash
python -m pip install scikit-learn polars
```

### 5. OpenBB Integration

Install the selected OpenBB extensions:

```bash
python -m pip install \
  "openbb-core[pandas]" \
  openbb-sec \
  openbb-fred \
  openbb-cboe \
  openbb-nasdaq \
  openbb-news
```

Generate the OpenBB interface:

```bash
openbb-build
```

Some providers require API keys or specific data-access permissions.

## Verification

Compile the source:

```bash
python -m compileall -q src/lqie
```

Run the complete test suite:

```bash
python -m pytest -v
```

## Performance Benchmarks

### Quantitative Mathematics

```bash
python benchmarks/bench_quant.py \
  --iterations 100 \
  --batches 5
```

### Financial Data Normalization

```bash
python benchmarks/bench_data.py \
  --rows 5000 \
  --iterations 20 \
  --batches 5
```

Benchmark results should be compared using the same hardware, Python version and software environment.

## Development Roadmap

| Version | Development Objective |
|---|---|
| 0.1 | Deterministic financial mathematics |
| 0.2 | Advanced quantitative mathematics |
| 0.3 | Neural network foundation and data integration |
| 0.3.1 | Financial feature engineering and dataset pipeline |
| 0.4 | Advanced neural forecasting architectures |
| 0.5 | Training and evaluation infrastructure |
| 1.0 | Integrated quantitative intelligence engine |

## Engineering Principles

1. Mathematical correctness takes priority over model complexity.
2. Financial calculations must be deterministic and independently verifiable.
3. Predictive models must undergo out-of-sample evaluation.
4. Training and testing must respect chronological data boundaries.
5. Data leakage must be prevented.
6. Every release must include automated tests and performance benchmarks.
7. Model predictions must communicate uncertainty.
8. External data sources must respect their licensing and redistribution restrictions.

## Current Development Environment

| Component | Configuration |
|---|---|
| Operating System | Ubuntu on WSL2 |
| Python | 3.12 |
| PyTorch | 2.14.1+cu130 |
| CUDA | 13.0 |
| GPU | NVIDIA GeForce RTX 4050 Laptop GPU |
| Data Integration | OpenBB |
| Runtime | Python |

## Important Notice

LQIE is an experimental quantitative research and software development project.

Its predictive models have not yet established production-grade financial forecasting performance. Benchmark results and successful software tests do not establish investment profitability.

All predictive capabilities require rigorous independent validation before practical financial deployment.

---

**LQIE — Lionare Quantitative Intelligence Engine**

*Numerical intelligence for financial markets.*
