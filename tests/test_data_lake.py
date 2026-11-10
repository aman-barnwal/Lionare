import polars as pl
import pytest

from lqie.data.lake import (
    DuckDBCatalog,
    LakePaths,
    ManifestManager,
    SourceDefinition,
    SourceRegistry,
    write_parquet,
)


def test_lake_paths_create_expected_directories(tmp_path):
    lake = LakePaths(tmp_path / "lake").ensure()

    assert lake.bronze.is_dir()
    assert lake.silver.is_dir()
    assert lake.gold.is_dir()
    assert lake.catalog.is_dir()
    assert lake.metadata.is_dir()


def test_lake_rejects_paths_outside_root(tmp_path):
    lake = LakePaths(tmp_path / "lake").ensure()

    with pytest.raises(ValueError):
        lake.relative_path(tmp_path / "outside.csv")


def test_source_registry_round_trip(tmp_path):
    lake = LakePaths(tmp_path / "lake").ensure()
    registry = SourceRegistry(lake=lake)

    source = SourceDefinition(
        source_id="test_source",
        name="Test Data Source",
        homepage="https://example.com",
        license_name="CC0",
        access_method="public_download",
        update_frequency="daily",
        categories=("equities", "fundamentals"),
    )

    registry.register(source)

    loaded = registry.get("test_source")
    assert loaded.name == source.name
    assert loaded.categories == ("equities", "fundamentals")
    assert registry.list_sources() == [source]


def test_source_registry_duplicate_protection(tmp_path):
    registry = SourceRegistry(lake=LakePaths(tmp_path / "lake").ensure())

    source = SourceDefinition(
        source_id="source_a",
        name="Source A",
        homepage="https://example.com",
    )

    registry.register(source)

    with pytest.raises(ValueError):
        registry.register(source, replace=False)


def test_manifest_records_and_verifies_file(tmp_path):
    lake = LakePaths(tmp_path / "lake").ensure()
    source_file = lake.bronze / "sample.csv"
    source_file.write_text(
        "date,value\n2026-01-01,100\n",
        encoding="utf-8",
    )

    manifest = ManifestManager(lake=lake)
    entry = manifest.record_file(
        file_path=source_file,
        source_id="test_source",
        dataset="sample_prices",
        retrieval_method="test_download",
    )

    assert entry["size_bytes"] == source_file.stat().st_size
    assert manifest.verify_entry(entry)
    assert len(manifest.entries()) == 1

    source_file.write_text("changed data", encoding="utf-8")
    assert not manifest.verify_entry(entry)


def test_manifest_rejects_file_outside_lake(tmp_path):
    lake = LakePaths(tmp_path / "lake").ensure()
    outside = tmp_path / "outside.csv"
    outside.write_text("sample", encoding="utf-8")

    manifest = ManifestManager(lake=lake)

    with pytest.raises(ValueError):
        manifest.record_file(
            outside,
            source_id="test_source",
            dataset="test",
            retrieval_method="test",
        )


def test_parquet_write_and_duckdb_query(tmp_path):
    lake = LakePaths(tmp_path / "lake").ensure()

    frame = pl.DataFrame(
        {
            "symbol": ["AAA", "BBB", "CCC"],
            "close": [100.0, 200.0, 300.0],
        }
    )

    parquet_file = write_parquet(
        frame,
        lake.silver / "prices" / "sample.parquet",
    )

    assert parquet_file.is_file()

    with DuckDBCatalog(lake=lake) as catalog:
        catalog.register_parquet_view("sample_prices", parquet_file)

        rows = catalog.query(
            "SELECT symbol, close FROM sample_prices ORDER BY symbol"
        )

        assert rows == [
            ("AAA", 100.0),
            ("BBB", 200.0),
            ("CCC", 300.0),
        ]
        assert "sample_prices" in catalog.list_views()


def test_catalog_rejects_unsafe_view_name(tmp_path):
    lake = LakePaths(tmp_path / "lake").ensure()
    parquet_file = write_parquet(
        pl.DataFrame({"value": [1]}),
        lake.silver / "sample.parquet",
    )

    with DuckDBCatalog(lake=lake) as catalog:
        with pytest.raises(ValueError):
            catalog.register_parquet_view(
                "sample; DROP TABLE users",
                parquet_file,
            )
