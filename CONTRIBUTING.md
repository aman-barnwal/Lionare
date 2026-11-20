# Contributing to Lionare

Thank you for contributing to Lionare and LQIE.

## Requirements
- Python >=3.12 and <3.14
- Git and pip
- PyTorch for neural network tests

## Installation
Clone the repository and enter its directory.

    git clone https://github.com/aman-barnwal/Lionare.git
    cd Lionare

Create a virtual environment.

    python3 -m venv .venv
    source .venv/bin/activate
    python -m pip install --upgrade pip
    python -m pip install -e ".[dev]"

Install CPU PyTorch for testing.

    python -m pip install torch --index-url https://download.pytorch.org/whl/cpu

## Verification

    python -m compileall -q src
    python -m pytest -q

## Contribution Guidelines

1. Keep financial calculations deterministic and testable.
2. Validate numerical inputs and edge cases.
3. Avoid look-ahead bias in financial forecasting.
4. Preserve chronological separation between training and evaluation.
5. Add tests for new mathematical functionality.
6. Never commit credentials, API keys or private datasets.
7. Keep contributions focused and document technical decisions.

## Pull Requests

1. Create a separate feature branch.
2. Make a focused contribution.
3. Run relevant tests.
4. Use descriptive commit messages.
5. Explain changes and verification in the pull request.
6. Link related issues using GitHub closing keywords.

Thank you for helping improve Lionare.
