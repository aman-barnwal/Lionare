"""Shared input validation for numerical quantitative routines."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np


def finite_float(value: Any, name: str) -> float:
    if isinstance(value, (bool, np.bool_)):
        raise TypeError(f"{name} must be numeric, not bool")
    try:
        result = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"{name} must be numeric") from exc
    if not math.isfinite(result):
        raise ValueError(f"{name} must be finite")
    return result


def vector(values: Sequence[Any], name: str, *, min_size: int = 1) -> np.ndarray:
    if isinstance(values, (str, bytes)):
        raise TypeError(f"{name} must be a numeric sequence")
    try:
        items = list(values)
    except TypeError as exc:
        raise TypeError(f"{name} must be a numeric sequence") from exc
    if len(items) < min_size:
        raise ValueError(f"{name} must contain at least {min_size} observations")
    return np.asarray([finite_float(x, name) for x in items], dtype=np.float64)


def return_series(values: Sequence[Any], name: str = "returns") -> np.ndarray:
    arr = vector(values, name, min_size=2)
    if np.any(arr <= -1.0):
        raise ValueError(f"{name} must contain simple returns greater than -1")
    return arr


def confidence_level(value: Any) -> float:
    confidence = finite_float(value, "confidence")
    if not 0.0 < confidence < 1.0:
        raise ValueError("confidence must be strictly between 0 and 1")
    return confidence


def asset_matrix(data: Mapping[str, Sequence[Any]]) -> tuple[tuple[str, ...], np.ndarray]:
    if not isinstance(data, Mapping) or not data:
        raise ValueError("returns must be a non-empty mapping of asset names to observations")
    names = tuple(data.keys())
    if any(not isinstance(name, str) or not name.strip() for name in names):
        raise ValueError("asset names must be non-empty strings")
    columns = [vector(data[name], f"returns[{name!r}]", min_size=2) for name in names]
    lengths = {len(column) for column in columns}
    if len(lengths) != 1:
        raise ValueError("all asset return series must have equal lengths")
    matrix = np.column_stack(columns)
    if np.any(matrix <= -1.0):
        raise ValueError("simple returns must be greater than -1")
    return names, matrix
