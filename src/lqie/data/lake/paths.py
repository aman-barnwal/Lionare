"""Canonical paths for the Lionare data lake."""

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class LakePaths:
    root: Path | str | None = None

    def __post_init__(self):
        value = self.root or os.environ.get(
            "LIONARE_DATA_HOME", "~/lionare-data"
        )
        object.__setattr__(self, "root", Path(value).expanduser().resolve())

    @property
    def bronze(self) -> Path:
        return self.root / "bronze"

    @property
    def silver(self) -> Path:
        return self.root / "silver"

    @property
    def gold(self) -> Path:
        return self.root / "gold"

    @property
    def catalog(self) -> Path:
        return self.root / "catalog"

    @property
    def metadata(self) -> Path:
        return self.root / "metadata"

    @property
    def source_registry_file(self) -> Path:
        return self.metadata / "source_registry" / "sources.json"

    @property
    def manifest_file(self) -> Path:
        return self.metadata / "manifests" / "manifest.jsonl"

    @property
    def duckdb_file(self) -> Path:
        return self.catalog / "lionare.duckdb"

    def ensure(self) -> "LakePaths":
        directories = [
            self.bronze,
            self.silver,
            self.gold,
            self.catalog,
            self.metadata / "source_registry",
            self.metadata / "manifests",
            self.metadata / "licenses",
            self.metadata / "quality",
        ]
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
        return self

    def relative_path(self, path: str | Path) -> str:
        resolved = Path(path).expanduser().resolve()
        try:
            return resolved.relative_to(self.root).as_posix()
        except ValueError as exc:
            raise ValueError(
                f"Path must be inside the data lake: {resolved}"
            ) from exc
