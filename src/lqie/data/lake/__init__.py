"""Lionare data-lake infrastructure."""

from lqie.data.lake.catalog import DuckDBCatalog
from lqie.data.lake.client import DataLakeClient
from lqie.data.lake.manifest import ManifestManager
from lqie.data.lake.parquet import write_parquet
from lqie.data.lake.paths import LakePaths
from lqie.data.lake.registry import SourceDefinition, SourceRegistry

__all__ = [
    "DataLakeClient",
    "DuckDBCatalog",
    "LakePaths",
    "ManifestManager",
    "SourceDefinition",
    "SourceRegistry",
    "write_parquet",
]
