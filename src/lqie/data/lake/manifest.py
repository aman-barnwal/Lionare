"""Checksummed file manifest for data-lake ingestion."""

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from lqie.data.lake.paths import LakePaths


class ManifestManager:
    def __init__(
        self,
        path: str | Path | None = None,
        lake: LakePaths | None = None,
    ):
        self.lake = lake or LakePaths()
        self.path = Path(path) if path else self.lake.manifest_file
        self.path.parent.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def sha256_file(path: str | Path) -> str:
        digest = hashlib.sha256()
        with Path(path).open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def record_file(
        self,
        file_path: str | Path,
        source_id: str,
        dataset: str,
        retrieval_method: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        file_path = Path(file_path).expanduser().resolve()

        if not file_path.is_file():
            raise FileNotFoundError(file_path)
        if not source_id.strip() or not dataset.strip():
            raise ValueError("source_id and dataset are required")

        entry = {
            "schema_version": 1,
            "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
            "source_id": source_id,
            "dataset": dataset,
            "path": self.lake.relative_path(file_path),
            "size_bytes": file_path.stat().st_size,
            "sha256": self.sha256_file(file_path),
            "retrieval_method": retrieval_method,
            "metadata": metadata or {},
        }

        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, sort_keys=True) + "\n")
            handle.flush()
            os.fsync(handle.fileno())

        return entry

    def entries(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []

        result = []
        with self.path.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                if line.strip():
                    try:
                        result.append(json.loads(line))
                    except json.JSONDecodeError as exc:
                        raise ValueError(
                            f"Invalid manifest JSON at line {line_number}"
                        ) from exc
        return result

    def verify_entry(self, entry: dict[str, Any]) -> bool:
        file_path = (self.lake.root / entry["path"]).resolve()

        try:
            file_path.relative_to(self.lake.root)
        except ValueError:
            return False

        if not file_path.is_file():
            return False

        return (
            file_path.stat().st_size == entry["size_bytes"]
            and self.sha256_file(file_path) == entry["sha256"]
        )
