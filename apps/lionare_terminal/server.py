"""Lionare Terminal 0.1 — integrated SEC company workstation."""

import json
import mimetypes
import time
from functools import lru_cache
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

import polars as pl

from lqie.data.lake import DataLakeClient, LakePaths
from lqie.models.fundamental_trend import forecast_annual_metric

APP_DIR = Path(__file__).resolve().parent
STATIC_DIR = (APP_DIR / "static").resolve()
LAKE = LakePaths().ensure()

FACTS_PATH = LAKE.silver / "fundamentals" / "sec_selected_facts.parquet"

COMPANIES = {
    "AAPL": ("Apple Inc.", "Technology"),
    "MSFT": ("Microsoft Corporation", "Technology"),
    "NVDA": ("NVIDIA Corporation", "Semiconductors"),
    "AMZN": ("Amazon.com Inc.", "Consumer / Cloud"),
    "GOOGL": ("Alphabet Inc.", "Technology"),
    "META": ("Meta Platforms Inc.", "Technology"),
    "JPM": ("JPMorgan Chase & Co.", "Banking"),
    "XOM": ("Exxon Mobil Corporation", "Energy"),
    "WMT": ("Walmart Inc.", "Retail"),
    "COST": ("Costco Wholesale Corporation", "Retail"),
}

METRICS = {
    "revenue": "Revenue",
    "net_income": "Net Income",
    "total_assets": "Total Assets",
    "operating_cash_flow": "Operating Cash Flow",
    "operating_income": "Operating Income",
}

TAG_PRIORITY = {
    "revenue": [
        "RevenueFromContractWithCustomerExcludingAssessedTax",
        "Revenues",
        "SalesRevenueNet",
        "RevenueFromContractWithCustomerIncludingAssessedTax",
    ],
    "net_income": ["NetIncomeLoss", "ProfitLoss"],
}

FLOW_METRICS = {
    "revenue",
    "net_income",
    "operating_cash_flow",
    "operating_income",
}

FACTS_CACHE = {"mtime": None, "frame": None}


def get_facts():
    if not FACTS_PATH.is_file():
        raise FileNotFoundError(
            f"SEC fundamentals dataset not found: {FACTS_PATH}"
        )

    mtime = FACTS_PATH.stat().st_mtime

    if FACTS_CACHE["mtime"] != mtime:
        FACTS_CACHE["frame"] = pl.read_parquet(FACTS_PATH)
        FACTS_CACHE["mtime"] = mtime

    return FACTS_CACHE["frame"]


def annual_series(symbol: str, metric: str) -> list[dict]:
    symbol = symbol.upper()
    metric = metric.lower()

    if symbol not in COMPANIES:
        raise ValueError(f"Unsupported company: {symbol}")

    if metric not in METRICS:
        raise ValueError(f"Unsupported metric: {metric}")

    frame = get_facts()

    required = {
        "ticker", "metric", "unit", "value", "period_end",
        "filed", "form", "fiscal_period", "tag",
    }

    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"SEC dataset is missing columns: {sorted(missing)}")

    rows = frame.filter(
        (pl.col("ticker") == symbol)
        & (pl.col("metric") == metric)
        & (pl.col("unit") == "USD")
    ).to_dicts()

    priorities = TAG_PRIORITY.get(metric, [])
    chosen = {}

    for row in rows:
        period_end = row.get("period_end")
        if not period_end:
            continue

        try:
            year = int(str(period_end)[:4])
            value = float(row["value"])
        except (TypeError, ValueError, KeyError):
            continue

        if not 2010 <= year <= 2026:
            continue

        if row.get("fiscal_period") not in ("FY", "Q4"):
            continue

        if metric in FLOW_METRICS and not row.get("period_start"):
            continue

        if not value == value or value in (float("inf"), float("-inf")):
            continue

        tag = row.get("tag", "")
        priority = priorities.index(tag) if tag in priorities else len(priorities)

        filed = str(row.get("filed") or "")
        score = (priority, filed)

        existing = chosen.get(year)
        if existing is None or score < existing["score"]:
            chosen[year] = {
                "score": score,
                "data": {
                    "year": year,
                    "date": str(period_end)[:10],
                    "value": value,
                    "usd_millions": value / 1_000_000,
                    "filed": filed,
                    "form": row.get("form"),
                    "tag": tag,
                    "unit": "USD",
                },
            }

    return [
        chosen[year]["data"]
        for year in sorted(chosen)
    ]


def company_summary(symbol: str) -> dict:
    symbol = symbol.upper()
    name, sector = COMPANIES[symbol]

    revenue = annual_series(symbol, "revenue")
    income = annual_series(symbol, "net_income")
    assets = annual_series(symbol, "total_assets")

    return {
        "symbol": symbol,
        "name": name,
        "sector": sector,
        "revenue_latest": revenue[-1] if revenue else None,
        "net_income_latest": income[-1] if income else None,
        "assets_latest": assets[-1] if assets else None,
        "revenue_years": len(revenue),
        "history_start": revenue[0]["year"] if revenue else None,
        "history_end": revenue[-1]["year"] if revenue else None,
    }


def read_headlines():
    path = LAKE.silver / "news" / "official_headlines.parquet"

    if not path.is_file():
        return []

    try:
        return pl.read_parquet(path).tail(100).to_dicts()[::-1]
    except Exception:
        return []


def read_events():
    path = LAKE.silver / "news" / "gdelt_events_latest.parquet"

    if not path.is_file():
        return []

    try:
        return pl.read_parquet(path).tail(100).to_dicts()[::-1]
    except Exception:
        return []


def overview():
    datasets = []
    try:
        with DataLakeClient(lake=LAKE) as client:
            datasets = client.dataset_summary()
    except Exception as exc:
        datasets = {"error": f"{type(exc).__name__}: {exc}"}

    files = [p for p in LAKE.root.rglob("*") if p.is_file()]
    total_bytes = sum(p.stat().st_size for p in files)

    health_path = LAKE.metadata / "quality" / "source_health.json"
    try:
        health = json.loads(health_path.read_text(encoding="utf-8"))
    except Exception:
        health = {}

    return {
        "version": "0.4.0",
        "storage_bytes": total_bytes,
        "datasets": datasets,
        "company_count": len(COMPANIES),
        "health": health,
        "last_fundamentals_update": (
            time.strftime(
                "%Y-%m-%d %H:%M:%S UTC",
                time.gmtime(FACTS_PATH.stat().st_mtime),
            )
            if FACTS_PATH.is_file()
            else None
        ),
    }


class Handler(BaseHTTPRequestHandler):
    def send_bytes(self, payload, content_type="application/json"):
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def send_json(self, value):
        self.send_bytes(
            json.dumps(value, default=str).encode("utf-8"),
            "application/json; charset=utf-8",
        )

    def error(self, code, message):
        payload = json.dumps({"error": message}).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = unquote(parsed.path)
        params = parse_qs(parsed.query)

        try:
            if path == "/api/overview":
                self.send_json(overview())
                return

            if path == "/api/companies":
                self.send_json([
                    company_summary(symbol)
                    for symbol in COMPANIES
                ])
                return

            if path == "/api/company":
                symbol = params.get("symbol", [""])[0].upper()
                if symbol not in COMPANIES:
                    self.error(404, "Company not in initial universe")
                    return

                result = company_summary(symbol)
                result["metrics"] = {
                    metric: annual_series(symbol, metric)
                    for metric in METRICS
                }
                self.send_json(result)
                return

            if path == "/api/series":
                symbol = params.get("symbol", ["AAPL"])[0].upper()
                metric = params.get("metric", ["revenue"])[0].lower()
                compare = params.get("compare", [""])[0]

                symbols = [symbol]
                symbols.extend(
                    x.strip().upper()
                    for x in compare.split(",")
                    if x.strip()
                )
                symbols = list(dict.fromkeys(symbols))[:5]

                data = {
                    item: annual_series(item, metric)
                    for item in symbols
                }

                self.send_json({
                    "metric": metric,
                    "label": METRICS[metric],
                    "unit": "USD",
                    "series": [
                        {
                            "symbol": item,
                            "name": COMPANIES[item][0],
                            "data": data[item],
                        }
                        for item in symbols
                    ],
                })
                return

            if path == "/api/forecast":
                symbol = params.get("symbol", ["AAPL"])[0].upper()
                metric = params.get("metric", ["revenue"])[0].lower()

                if symbol not in COMPANIES or metric not in METRICS:
                    self.error(400, "Invalid company or metric")
                    return

                observations = annual_series(symbol, metric)
                result = forecast_annual_metric(observations, horizon=3)

                self.send_json({
                    "symbol": symbol,
                    "company": COMPANIES[symbol][0],
                    "metric": metric,
                    "label": METRICS[metric],
                    **result,
                })
                return

            if path == "/api/news":
                self.send_json({
                    "headlines": read_headlines(),
                    "events": read_events(),
                })
                return

            if path == "/api/health":
                health_path = LAKE.metadata / "quality" / "source_health.json"
                if health_path.is_file():
                    self.send_bytes(health_path.read_bytes())
                else:
                    self.send_json({})
                return

            relative = "index.html" if path == "/" else path.lstrip("/")
            target = (STATIC_DIR / relative).resolve()

            if not target.is_relative_to(STATIC_DIR) or not target.is_file():
                self.error(404, "File not found")
                return

            content_type = mimetypes.guess_type(target.name)[0]
            self.send_bytes(
                target.read_bytes(),
                content_type or "application/octet-stream",
            )

        except FileNotFoundError as exc:
            self.error(503, str(exc))
        except ValueError as exc:
            self.error(400, str(exc))
        except Exception as exc:
            self.error(500, f"{type(exc).__name__}: {exc}")

    def log_message(self, fmt, *args):
        print("[Lionare]", fmt % args)


def main():
    host, port = "127.0.0.1", 8765

    if not FACTS_PATH.is_file():
        raise SystemExit(
            f"Missing SEC facts Parquet: {FACTS_PATH}. "
            "Run the SEC ingestion script first."
        )

    print("==========================================")
    print("       LIONARE TERMINAL v0.1")
    print("==========================================")
    print("Companies:", ", ".join(COMPANIES))
    print("Data lake:", LAKE.root)
    print(f"Local terminal: http://{host}:{port}")
    print("Charts: historical SEC fundamentals")
    print("Live share-price feed: not connected")
    print("LQIE: experimental fundamental trend baseline")
    print("Press Ctrl+C to stop.")

    ThreadingHTTPServer((host, port), Handler).serve_forever()


if __name__ == "__main__":
    main()
