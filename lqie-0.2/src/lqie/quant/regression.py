"""Ordinary least-squares regression using NumPy's stable least-squares solver."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

import numpy as np

from ._validation import vector


@dataclass(frozen=True, slots=True)
class OLSResult:
    """OLS estimates and fit diagnostics in input feature order."""

    intercept: float
    coefficients: tuple[float, ...]
    feature_names: tuple[str, ...]
    r_squared: float
    residual_standard_error: float | None
    observations: int
    rank: int
    fitted_values: tuple[float, ...]
    residuals: tuple[float, ...]


def fit_ols(
    y: Sequence[Any],
    X: Sequence[Sequence[Any]] | Sequence[Any],
    *,
    feature_names: Sequence[str] | None = None,
    fit_intercept: bool = True,
) -> OLSResult:
    """Fit OLS by minimizing squared residuals with ``numpy.linalg.lstsq``.

    ``X`` may be a one-dimensional single-feature sequence or a 2-D matrix.
    Rank-deficient inputs are allowed; ``rank`` reports the design-matrix rank
    so callers can detect collinearity. Residual standard error is ``None`` if
    no residual degrees of freedom remain.
    """
    target = vector(y, "y", min_size=2)
    if isinstance(X, (str, bytes)):
        raise TypeError("X must be a numeric vector or matrix")
    try:
        raw = np.asarray(X, dtype=object)
    except (TypeError, ValueError) as exc:
        raise ValueError("X must be a rectangular numeric vector or matrix") from exc
    if raw.ndim == 1:
        raw = raw.reshape(-1, 1)
    if raw.ndim != 2 or raw.shape[0] != target.size or raw.shape[1] < 1:
        raise ValueError("X must have shape (observations, features) matching y")
    if raw.shape[0] < 2:
        raise ValueError("at least two observations are required")
    x = np.empty(raw.shape, dtype=np.float64)
    for index, value in np.ndenumerate(raw):
        if isinstance(value, (bool, np.bool_)):
            raise TypeError("X must be numeric, not bool")
        try:
            number = float(value)
        except (TypeError, ValueError, OverflowError) as exc:
            raise ValueError("X must contain only numeric values") from exc
        if not np.isfinite(number):
            raise ValueError("X must contain only finite values")
        x[index] = number

    feature_count = int(x.shape[1])
    if feature_names is None:
        names = tuple(f"x{i + 1}" for i in range(feature_count))
    else:
        names = tuple(feature_names)
        if len(names) != feature_count or any(not isinstance(n, str) or not n.strip() for n in names):
            raise ValueError("feature_names must contain one non-empty name per feature")

    design = np.column_stack((np.ones(target.size), x)) if fit_intercept else x
    coefficients, _, rank, _ = np.linalg.lstsq(design, target, rcond=None)
    fitted = design @ coefficients
    residuals = target - fitted
    sse = float(residuals @ residuals)
    centered_target = target - target.mean()
    sst = float(centered_target @ centered_target)
    if sst == 0.0:
        r_squared = 1.0 if sse <= np.finfo(float).eps else 0.0
    else:
        r_squared = 1.0 - sse / sst
    degrees_of_freedom = int(target.size - rank)
    residual_se = float(np.sqrt(sse / degrees_of_freedom)) if degrees_of_freedom > 0 else None

    intercept = float(coefficients[0]) if fit_intercept else 0.0
    slopes = coefficients[1:] if fit_intercept else coefficients
    return OLSResult(
        intercept=intercept,
        coefficients=tuple(float(v) for v in slopes),
        feature_names=names,
        r_squared=float(r_squared),
        residual_standard_error=residual_se,
        observations=int(target.size),
        rank=int(rank),
        fitted_values=tuple(float(v) for v in fitted),
        residuals=tuple(float(v) for v in residuals),
    )
