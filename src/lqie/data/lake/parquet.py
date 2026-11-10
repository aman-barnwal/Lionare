"""Atomic, compressed Parquet persistence for Lionare."""

import os
import uuid
from pathlib import Path


def write_parquet(
    frame,
    path: str | Path,
    compression: str = "zstd",
) -> Path:
    """Persist a Polars DataFrame atomically as compressed Parquet."""
    import polars as pl

    destination = Path(path).expanduser().resolve()

    if destination.suffix.lower() != ".parquet":
        raise ValueError("Destination must have a .parquet extension")

    if isinstance(frame, pl.LazyFrame):
        frame = frame.collect()
    elif not isinstance(frame, pl.DataFrame):
        frame = pl.DataFrame(frame)

    if frame.is_empty():
        raise ValueError("Refusing to write an empty Parquet dataset")

    destination.parent.mkdir(parents=True, exist_ok=True)

    temporary = destination.with_name(
        f".{destination.stem}.{uuid.uuid4().hex}.tmp.parquet"
    )

    try:
        frame.write_parquet(
            temporary,
            compression=compression,
            statistics=True,
        )
        os.replace(temporary, destination)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise

    return destination
