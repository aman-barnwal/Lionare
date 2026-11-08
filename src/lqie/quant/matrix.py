"""Cross-sectional and time-series matrix statistics."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

import numpy as np

from ._validation import asset_matrix


@dataclass(frozen=True, slots=True)
class MatrixEstimate:
    """A named square matrix with observations and estimator convention."""

    assets: tuple[str, ...]
    values: tuple[tuple[float, ...], ...]
    observations: int
    ddof: int = 1


def covariance_matrix(returns: Mapping[str, Sequence[Any]]) -> MatrixEstimate:
    """Return the sample covariance matrix of aligned simple-return series.

    Rows are observations and columns follow the insertion order of ``returns``.
    Uses the unbiased sample estimator (ddof=1). All series must share the same
    observation calendar and must not contain missing values.
    """
    names, matrix = asset_matrix(returns)
    centered = matrix - matrix.mean(axis=0)
    covariance = (centered.T @ centered) / (matrix.shape[0] - 1)
    return MatrixEstimate(
        assets=names,
        values=tuple(tuple(float(x) for x in row) for row in covariance),
        observations=int(matrix.shape[0]),
    )


def correlation_matrix(returns: Mapping[str, Sequence[Any]]) -> MatrixEstimate:
    """Return Pearson correlations for aligned simple-return series.

    Raises ``ValueError`` when any input series has zero sample variance,
    because its correlation is undefined.
    """
    names, matrix = asset_matrix(returns)
    # Detect exactly constant input series before centering; floating-point
    # mean rounding can otherwise produce a tiny non-zero standard deviation.
    if np.any(np.ptp(matrix, axis=0) == 0.0):
        raise ValueError("correlation is undefined for an asset with zero variance")
    standard_deviations = matrix.std(axis=0, ddof=1)
    if np.any(standard_deviations == 0.0):
        raise ValueError("correlation is undefined for an asset with zero variance")
    centered = matrix - matrix.mean(axis=0)
    covariance = (centered.T @ centered) / (matrix.shape[0] - 1)
    correlation = covariance / np.outer(standard_deviations, standard_deviations)
    # Clip tiny floating-point excursions outside [-1, 1].
    correlation = np.clip(correlation, -1.0, 1.0)
    return MatrixEstimate(
        assets=names,
        values=tuple(tuple(float(x) for x in row) for row in correlation),
        observations=int(matrix.shape[0]),
    )
