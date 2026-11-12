"""Standardised detection results for LQIE."""

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

import numpy as np


def json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(v) for v in value]
    if isinstance(value, np.generic):
        return json_safe(value.item())
    if hasattr(value, "to_pydatetime"):
        return value.to_pydatetime().isoformat()
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if isinstance(value, float) and not np.isfinite(value):
        return None
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


@dataclass(slots=True)
class PatternDetection:
    symbol: str
    timeframe: str
    engine: str
    category: str
    pattern: str
    direction: str = "neutral"
    detected_at_utc: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    start_time: str | None = None
    end_time: str | None = None
    start_index: int | None = None
    end_index: int | None = None
    reference_price: float | None = None
    algorithm_score: float | None = None
    is_prediction: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        result = asdict(self)
        return json_safe(result)
