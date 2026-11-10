"""Local web server for Lionare Terminal."""

import json
import mimetypes
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import urlparse, unquote

import polars as pl

from lqie.data.lake import DataLakeClient, LakePaths

APP_DIR = Path(__file__).resolve().parent
STATIC_DIR = (APP_DIR / "static").resolve()
LAKE = LakePaths().ensure()


def read_json(path):
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def dataset_summary():
    try:
        with DataLakeClient(lake=LAKE) as client:
            return client.dataset_summary()
    except Exception as exc:
        return {"error": f"{type(exc).__name__}: {exc}"}


def read_parquet_rows(path, limit=100):
    if not path.is_file():
        return []

    try:
        frame = pl.read_parquet(path).tail(limit)
        return frame.to_dicts()
    except Exception:
        return []


def overview():
    datasets = dataset_summary()
    if isinstance(datasets, dict):
        datasets = []

    total_bytes = sum(
        path.stat().st_size
        for path in LAKE.root.rglob("*")
        if path.is_file()
    )

    health = read_json(
        LAKE.metadata / "quality" / "source_health.json"
    )

    return {
        "project": "Lionare Terminal",
        "version": "0.4.0",
        "checked_at_utc": health.get("checked_at_utc"),
        "dataset_count": len(datasets),
        "storage_bytes": total_bytes,
        "headline_count": len(
            read_parquet_rows(
                LAKE.silver / "news" / "official_headlines.parquet",
                limit=1500,
            )
        ),
        "event_count": len(
            read_parquet_rows(
                LAKE.silver / "news" / "gdelt_events_latest.parquet",
                limit=100000,
            )
        ),
        "health": health,
        "datasets": datasets,
    }


class Handler(BaseHTTPRequestHandler):
    def send_data(self, payload, content_type):
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def send_json(self, value):
        payload = json.dumps(value, default=str).encode("utf-8")
        self.send_data(payload, "application/json; charset=utf-8")

    def do_GET(self):
        path = unquote(urlparse(self.path).path)

        if path == "/api/overview":
            self.send_json(overview())
            return

        if path == "/api/datasets":
            self.send_json(dataset_summary())
            return

        if path == "/api/health":
            self.send_json(
                read_json(
                    LAKE.metadata / "quality" / "source_health.json"
                )
            )
            return

        if path == "/api/news":
            headlines = read_parquet_rows(
                LAKE.silver / "news" / "official_headlines.parquet",
                limit=100,
            )
            events = read_parquet_rows(
                LAKE.silver / "news" / "gdelt_events_latest.parquet",
                limit=100,
            )
            self.send_json({
                "headlines": list(reversed(headlines)),
                "events": list(reversed(events)),
            })
            return

        relative = "index.html" if path == "/" else path.lstrip("/")
        target = (STATIC_DIR / relative).resolve()

        if not target.is_relative_to(STATIC_DIR) or not target.is_file():
            self.send_response(404)
            self.end_headers()
            return

        content_type = mimetypes.guess_type(target.name)[0]
        content_type = content_type or "application/octet-stream"

        self.send_data(
            target.read_bytes(),
            f"{content_type}; charset=utf-8",
        )

    def log_message(self, fmt, *args):
        print("[Lionare]", fmt % args)


def main():
    host = "127.0.0.1"
    port = 8765
    print("========================================")
    print("       LIONARE FINANCIAL TERMINAL       ")
    print("========================================")
    print(f"Data lake: {LAKE.root}")
    print(f"Open: http://{host}:{port}")
    print("Press Ctrl+C to stop.")
    HTTPServer((host, port), Handler).serve_forever()


if __name__ == "__main__":
    main()
