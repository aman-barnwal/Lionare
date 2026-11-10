import polars as pl

from lqie.data.lake import DataLakeClient, LakePaths, write_parquet


def test_client_discovers_and_queries_silver_datasets(tmp_path):
    lake = LakePaths(tmp_path / "lake").ensure()

    write_parquet(
        pl.DataFrame({
            "symbol": ["AAA", "BBB"],
            "close": [100.0, 200.0],
        }),
        lake.silver / "prices" / "sample.parquet",
    )

    with DataLakeClient(lake=lake) as client:
        assert "ds_prices_sample" in client.list_datasets()

        result = client.query(
            "SELECT COUNT(*) FROM ds_prices_sample"
        )
        assert result == [(2,)]

        summary = client.dataset_summary()
        assert len(summary) == 1
        assert summary[0]["rows"] == 2
