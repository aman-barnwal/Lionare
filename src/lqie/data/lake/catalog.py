"""DuckDB catalogue for querying Lionare Parquet datasets."""

import re
from pathlib import Path

from lqie.data.lake.paths import LakePaths


_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class DuckDBCatalog:
    def __init__(
        self,
        database_path: str | Path | None = None,
        lake: LakePaths | None = None,
        read_only: bool = False,
    ):
        import duckdb

        self.lake = lake or LakePaths()
        self.database_path = (
            Path(database_path)
            if database_path is not None
            else self.lake.duckdb_file
        )

        if str(self.database_path) != ":memory:":
            self.database_path = self.database_path.expanduser().resolve()
            self.database_path.parent.mkdir(parents=True, exist_ok=True)

        self.connection = duckdb.connect(
            str(self.database_path),
            read_only=read_only,
        )

    def register_parquet_view(
        self,
        view_name: str,
        parquet_path: str | Path,
    ) -> None:
        if not _IDENTIFIER.fullmatch(view_name):
            raise ValueError(f"Invalid SQL view name: {view_name!r}")

        path = Path(parquet_path).expanduser().resolve()

        if path.is_dir():
            if not any(path.rglob("*.parquet")):
                raise FileNotFoundError(
                    f"No Parquet files found inside {path}"
                )
            source = str(path / "**" / "*.parquet")
        elif path.is_file() and path.suffix.lower() == ".parquet":
            source = str(path)
        else:
            raise FileNotFoundError(
                f"Expected an existing Parquet file or directory: {path}"
            )

        escaped_source = source.replace("'", "''")
        sql = (
            f'CREATE OR REPLACE VIEW "{view_name}" '
            f"AS SELECT * FROM read_parquet('{escaped_source}')"
        )
        self.connection.execute(sql)

    def execute(self, sql: str, parameters=None):
        return self.connection.execute(sql, parameters or [])

    def query(self, sql: str, parameters=None) -> list[tuple]:
        return self.execute(sql, parameters).fetchall()

    def list_views(self) -> list[str]:
        rows = self.query(
            """
            SELECT table_name
            FROM information_schema.views
            WHERE table_schema = 'main'
            ORDER BY table_name
            """
        )
        return [row[0] for row in rows]

    def close(self) -> None:
        self.connection.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
