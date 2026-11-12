from __future__ import annotations

import os
from pathlib import Path

APP_NAME = "Lionare Terminal"
APP_VERSION = "0.1.2"
DEFAULT_API_URL = "http://127.0.0.1:8765"
API_BASE_URL = os.environ.get("LIONARE_API_URL", DEFAULT_API_URL).rstrip("/")
DATA_LAKE_ROOT = Path(os.environ.get("LIONARE_DATA_LAKE", str(Path.home() / "lionare-data"))).expanduser()
REFRESH_INTERVAL_MS = max(15_000, int(os.environ.get("LIONARE_REFRESH_INTERVAL_MS", "15000")))

WATCHLIST = [
    ("AAPL", "Apple Inc."),
    ("MSFT", "Microsoft Corporation"),
    ("NVDA", "NVIDIA Corporation"),
    ("AMZN", "Amazon.com Inc."),
    ("GOOGL", "Alphabet Inc."),
    ("META", "Meta Platforms Inc."),
    ("JPM", "JPMorgan Chase & Co."),
    ("XOM", "Exxon Mobil Corporation"),
    ("WMT", "Walmart Inc."),
    ("COST", "Costco Wholesale Corporation"),
]

GLOBAL_MARKETS = [
    ("S&P 500", "United States"),
    ("NASDAQ Composite", "United States"),
    ("DOW JONES", "United States"),
    ("RUSSELL 2000", "United States"),
    ("FTSE 100", "United Kingdom"),
    ("DAX", "Germany"),
    ("NIFTY 50", "India"),
    ("NIKKEI 225", "Japan"),
    ("HANG SENG", "Hong Kong"),
]
