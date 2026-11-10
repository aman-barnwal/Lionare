"""Registry of financial data sources and their usage terms."""

import json
import os
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from lqie.data.lake.paths import LakePaths


_SOURCE_ID = re.compile(r"^[a-z0-9][a-z0-9._-]*$")


@dataclass(frozen=True, slots=True)
class SourceDefinition:
    source_id: str
    name: str
    homepage: str
    license_name: str = "unknown"
    terms_url: str = ""
    access_method: str = "public_download"
    update_frequency: str = "unspecified"
    categories: tuple[str, ...] = ()
    api_key_required: bool = False
    attribution: str = ""
    notes: str = ""

    def validate(self) -> None:
        if not _SOURCE_ID.fullmatch(self.source_id):
            raise ValueError(f"Invalid source_id: {self.source_id!r}")
        if not self.name.strip():
            raise ValueError("Source name cannot be empty")
        if self.access_method not in {
            "public_download",
            "public_endpoint",
            "licensed_feed",
            "manual",
            "local",
        }:
            raise ValueError(
                f"Unsupported access_method: {self.access_method}"
            )


class SourceRegistry:
    def __init__(
        self,
        path: str | Path | None = None,
        lake: LakePaths | None = None,
    ):
        self.lake = lake or LakePaths()
        self.path = Path(path) if path else self.lake.source_registry_file
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def _read(self) -> dict[str, dict[str, Any]]:
        if not self.path.exists():
            return {}
        with self.path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        if not isinstance(data, dict):
            raise ValueError("Source registry must contain a JSON object")
        return data

    def _write(self, data: dict[str, dict[str, Any]]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        with temporary.open("w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, self.path)

    def register(
        self,
        source: SourceDefinition | dict[str, Any],
        replace: bool = True,
    ) -> None:
        if isinstance(source, dict):
            source = SourceDefinition(**source)
        if not isinstance(source, SourceDefinition):
            raise TypeError("source must be SourceDefinition or dict")

        source.validate()
        data = self._read()

        if source.source_id in data and not replace:
            raise ValueError(f"Source already registered: {source.source_id}")

        item = asdict(source)
        item["categories"] = list(source.categories)
        data[source.source_id] = item
        self._write(data)

    def get(self, source_id: str) -> SourceDefinition:
        data = self._read()
        try:
            item = data[source_id]
        except KeyError as exc:
            raise KeyError(f"Unknown data source: {source_id}") from exc

        item["categories"] = tuple(item.get("categories", ()))
        return SourceDefinition(**item)

    def list_sources(self) -> list[SourceDefinition]:
        sources = []
        for item in self._read().values():
            item["categories"] = tuple(item.get("categories", ()))
            sources.append(SourceDefinition(**item))
        return sorted(sources, key=lambda item: item.source_id)

    def remove(self, source_id: str) -> bool:
        data = self._read()
        if source_id not in data:
            return False
        del data[source_id]
        self._write(data)
        return True
