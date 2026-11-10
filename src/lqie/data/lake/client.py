"""Unified data-lake client for LQIE 0.4."""

import re
from pathlib import Path

from lqie.data.lake.catalog import DuckDBCatalog
from lqie.data.lake.paths import LakePaths


class DataLakeClient:
    """Discover Silver Parquet datasets and query them through DuckDB."""

    def __init__(self, lake: LakePaths | None = None):
        self.paths = (lake or LakePaths()).ensure()
        self.catalog = DuckDBCatalog(lake=self.paths)
        self._datasets: dict[str, Path] = {}
        self.refresh()

    @staticmethod
    def _view_name(path: Path) -> str:
        parts = path.with_suffix("").parts
        value = "ds_" + "_".join(parts)
        value = re.sub(r"[^A-Za-z0-9_]", "_", value)
        return value.lower()

    def refresh(self) -> list[str]:
        """Discover all Silver Parquet files and register SQL views."""
        discovered = {}

        for path in sorted(self.paths.silver.rglob("*.parquet")):
            relative = path.relative_to(self.paths.silver)
            view_name = self._view_name(relative)

            if view_name in discovered:
                raise ValueError(f"Duplicate dataset view: {view_name}")

            self.catalog.register_parquet_view(view_name, path)
            discovered[view_name] = path

        self._datasets = discovered
        return self.list_datasets()

    def list_datasets(self) -> list[str]:
        return sorted(self._datasets)

    def query(self, sql: str, parameters=None) -> list[tuple]:
        """Execute a SQL query against registered Silver datasets."""
        return self.catalog.query(sql, parameters)

    def dataset_summary(self) -> list[dict]:
        """Return row counts and disk sizes for registered datasets."""
        result = []

        for name, path in sorted(self._datasets.items()):
            count = self.catalog.query(
                f'SELECT COUNT(*) FROM "{name}"'
            )[0][0]

            result.append({
                "name": name,
                "path": str(path),
                "rows": count,
                "size_bytes": path.stat().st_size,
                "modified_at": path.stat().st_mtime,
            })

        return result

    def close(self) -> None:
        self.catalog.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
