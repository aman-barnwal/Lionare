"""Compact financial data acquisition for Lionare LQIE 0.4."""

import csv
import io
import json
import math
import os
import re
import sys
import time
from dataclasses import asdict
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import polars as pl

from lqie.data.lake import (
    LakePaths,
    ManifestManager,
    SourceDefinition,
    SourceRegistry,
    write_parquet,
)

TODAY = date.today().isoformat()
START_DATE = "2021-01-01"

SEC_TICKERS = [
    "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL",
    "META", "JPM", "XOM", "WMT", "COST",
]

FRED_SERIES = [
    "DGS10", "DGS2", "FEDFUNDS", "CPIAUCSL",
    "CPILFESL", "UNRATE", "PAYEMS", "GDPC1",
    "DEXINUS", "VIXCLS", "DCOILWTICO", "T10Y2Y",
    "DTWEXBGS", "M2SL",
]

MARKET_SYMBOLS = [
    "SPY", "QQQ", "IWM", "DIA",
    "AAPL", "MSFT", "NVDA", "JPM",
]

FACT_METRICS = {
    "RevenueFromContractWithCustomerExcludingAssessedTax": "revenue",
    "RevenueFromContractWithCustomerIncludingAssessedTax": "revenue",
    "SalesRevenueNet": "revenue",
    "Revenues": "revenue",
    "NetIncomeLoss": "net_income",
    "ProfitLoss": "net_income",
    "Assets": "total_assets",
    "Liabilities": "total_liabilities",
    "CashAndCashEquivalentsAtCarryingValue": "cash_and_equivalents",
    "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents":
        "cash_and_equivalents",
    "LongTermDebt": "long_term_debt",
    "LongTermDebtCurrent": "current_long_term_debt",
    "LongTermDebtNoncurrent": "long_term_debt",
    "NetCashProvidedByUsedInOperatingActivities": "operating_cash_flow",
    "EarningsPerShareDiluted": "diluted_eps",
    "EarningsPerShareBasic": "basic_eps",
    "OperatingIncomeLoss": "operating_income",
    "GrossProfit": "gross_profit",
    "EntityCommonStockSharesOutstanding": "shares_outstanding",
}

lake = LakePaths().ensure()
registry = SourceRegistry(lake=lake)
manifest = ManifestManager(lake=lake)

SEC_EMAIL = os.environ.get("SEC_CONTACT_EMAIL", "").strip()

if not SEC_EMAIL:
    SEC_EMAIL = input("Enter contact email for SEC User-Agent: ").strip()

if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", SEC_EMAIL):
    raise SystemExit("A valid contact email is required for SEC access.")

USER_AGENT = f"Lionare LQIE 0.4 Research contact: {SEC_EMAIL}"


def fetch_bytes(url: str, attempts: int = 4) -> bytes:
    """Download with retries and an identifiable User-Agent."""
    request = Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "*/*",
        },
    )

    for attempt in range(attempts):
        try:
            with urlopen(request, timeout=45) as response:
                return response.read()

        except HTTPError as exc:
            retryable = exc.code == 429 or exc.code >= 500
            if not retryable or attempt == attempts - 1:
                raise

        except (URLError, TimeoutError):
            if attempt == attempts - 1:
                raise

        time.sleep(2 ** attempt)

    raise RuntimeError(f"Download failed: {url}")


def is_fresh(path: Path, hours: int) -> bool:
    if not path.is_file():
        return False
    age = time.time() - path.stat().st_mtime
    return age < hours * 3600


def atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".part")

    try:
        with temporary.open("wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def register_sources() -> None:
    sources = [
        SourceDefinition(
            source_id="sec_edgar",
            name="US Securities and Exchange Commission",
            homepage="https://www.sec.gov/",
            license_name="SEC and filing-specific terms; review redistribution rights",
            terms_url="https://www.sec.gov/privacy.htm",
            access_method="public_endpoint",
            update_frequency="Filing-driven",
            categories=("fundamentals", "company_reference", "filings"),
            api_key_required=False,
            notes="Individual company-facts JSON; User-Agent required.",
        ),
        SourceDefinition(
            source_id="fred",
            name="Federal Reserve Economic Data",
            homepage="https://fred.stlouisfed.org/",
            license_name="Series-specific terms; inspect source attribution",
            terms_url="https://fred.stlouisfed.org/",
            access_method="public_download",
            update_frequency="Daily to quarterly, depending on series",
            categories=("macro", "rates", "fx", "commodities"),
            api_key_required=False,
            notes="Direct CSV graph downloads; five-year initial window.",
        ),
        SourceDefinition(
            source_id="cboe",
            name="Cboe historical market data through OpenBB",
            homepage="https://www.cboe.com/",
            license_name="Provider-specific terms; verify before redistribution",
            access_method="public_endpoint",
            update_frequency="Daily historical",
            categories=("equities", "etfs", "market_prices"),
            api_key_required=False,
            notes="Daily historical endpoint; not a live tick feed.",
        ),
        SourceDefinition(
            source_id="world_bank",
            name="World Bank Open Data",
            homepage="https://data.worldbank.org/",
            license_name="Dataset-specific terms; verify",
            terms_url="https://data.worldbank.org/",
            access_method="public_endpoint",
            update_frequency="Indicator-dependent",
            categories=("global_macro", "countries", "development"),
            api_key_required=False,
        ),
        SourceDefinition(
            source_id="cftc",
            name="US Commodity Futures Trading Commission",
            homepage="https://www.cftc.gov/",
            license_name="Official report terms; verify",
            terms_url="https://www.cftc.gov/MarketReports/CommitmentsofTraders/index.htm",
            access_method="public_download",
            update_frequency="Weekly",
            categories=("derivatives", "futures", "positioning"),
            api_key_required=False,
        ),
        SourceDefinition(
            source_id="gdelt",
            name="GDELT Project",
            homepage="https://www.gdeltproject.org/",
            license_name="Source terms; verify",
            access_method="public_download",
            update_frequency="Frequent event updates",
            categories=("news", "events", "geopolitics"),
            api_key_required=False,
        ),
    ]

    for source in sources:
        registry.register(source)

    print(f"Registered {len(sources)} data sources.")


def acquire_sec() -> int:
    print("\n========== SEC COMPANY FUNDAMENTALS ==========")

    reference_path = (
        lake.bronze / "reference" / "sec" / "company_tickers.json"
    )

    if is_fresh(reference_path, 168):
        mapping = load_json(reference_path)
        print("Using cached SEC ticker mapping.")
    else:
        url = "https://www.sec.gov/files/company_tickers.json"
        payload = fetch_bytes(url)
        mapping = json.loads(payload)

        atomic_write(reference_path, payload)
        manifest.record_file(
            reference_path,
            "sec_edgar",
            "company_ticker_mapping",
            "SEC public download",
        )

    entries = list(mapping.values()) if isinstance(mapping, dict) else mapping

    ticker_rows = []
    lookup = {}

    for item in entries:
        ticker = str(item.get("ticker", "")).upper().strip()
        cik = int(item["cik_str"])
        title = str(item.get("title", ""))

        if ticker:
            ticker_rows.append({
                "ticker": ticker,
                "cik": cik,
                "company_name": title,
            })
            lookup[ticker] = {
                "cik": cik,
                "company_name": title,
            }

    if ticker_rows:
        write_parquet(
            pl.DataFrame(ticker_rows),
            lake.silver / "reference" / "sec_company_tickers.parquet",
        )

    fact_rows = []
    downloaded = 0
    failed = []

    for ticker in SEC_TICKERS:
        company = lookup.get(ticker)

        if company is None:
            print(f"SEC mapping missing: {ticker}")
            failed.append(ticker)
            continue

        cik = company["cik"]
        cik_padded = f"{cik:010d}"

        raw_path = (
            lake.bronze / "us" / "sec" / "companyfacts"
            / f"{ticker}_{cik_padded}.json"
        )

        try:
            if is_fresh(raw_path, 24):
                payload = load_json(raw_path)
                print(f"Cached: {ticker}")
            else:
                url = (
                    "https://data.sec.gov/api/xbrl/companyfacts/"
                    f"CIK{cik_padded}.json"
                )
                raw = fetch_bytes(url)
                payload = json.loads(raw)

                atomic_write(raw_path, raw)
                manifest.record_file(
                    raw_path,
                    "sec_edgar",
                    f"companyfacts_{ticker}",
                    "SEC individual company-facts endpoint",
                    {"ticker": ticker, "cik": cik},
                )
                downloaded += 1
                time.sleep(0.15)

            entity = payload.get("entityName", company["company_name"])

            for taxonomy, concepts in payload.get("facts", {}).items():
                if taxonomy not in {"us-gaap", "dei"}:
                    continue

                for tag, fact in concepts.items():
                    metric = FACT_METRICS.get(tag)
                    if metric is None:
                        continue

                    for unit, observations in fact.get("units", {}).items():
                        for observation in observations:
                            try:
                                value = float(observation["val"])
                            except (KeyError, TypeError, ValueError):
                                continue

                            if not math.isfinite(value):
                                continue

                            fact_rows.append({
                                "ticker": ticker,
                                "cik": cik,
                                "entity": entity,
                                "taxonomy": taxonomy,
                                "tag": tag,
                                "metric": metric,
                                "label": fact.get("label", ""),
                                "unit": unit,
                                "value": value,
                                "period_start": observation.get("start"),
                                "period_end": observation.get("end"),
                                "filed": observation.get("filed"),
                                "form": observation.get("form"),
                                "fiscal_year": observation.get("fy"),
                                "fiscal_period": observation.get("fp"),
                                "accession": observation.get("accn"),
                                "frame": observation.get("frame"),
                            })

            print(f"Processed: {ticker}")

        except Exception as exc:
            print(f"SEC ERROR {ticker}: {type(exc).__name__}: {exc}")
            failed.append(ticker)

    if fact_rows:
        facts_frame = pl.DataFrame(
            fact_rows,
            infer_schema_length=None,
        )

        destination = (
            lake.silver / "fundamentals" / "sec_selected_facts.parquet"
        )
        write_parquet(facts_frame, destination)

        manifest.record_file(
            destination,
            "sec_edgar",
            "selected_company_facts",
            "Normalised SEC company-facts JSON",
            {"companies": SEC_TICKERS, "rows": len(fact_rows)},
        )

        print("Fundamental observations:", len(fact_rows))
        print("Fundamentals Parquet:", destination)

    print("Company JSON files downloaded:", downloaded)
    print("Company failures:", failed)

    return len(fact_rows)


def acquire_fred() -> int:
    print("\n========== FRED MACROECONOMIC DATA ==========")

    grouped_rows = {
        "macro": [],
        "fx": [],
        "commodities": [],
        "market": [],
    }

    groups = {
        "DEXINUS": "fx",
        "DTWEXBGS": "fx",
        "DCOILWTICO": "commodities",
        "VIXCLS": "market",
    }

    successful = 0
    failed = []

    for series in FRED_SERIES:
        raw_path = lake.bronze / "global" / "fred" / f"{series}.csv"

        try:
            if is_fresh(raw_path, 24):
                csv_text = raw_path.read_text(encoding="utf-8-sig")
                print(f"Cached: {series}")
            else:
                params = urlencode({
                    "id": series,
                    "cosd": START_DATE,
                    "coed": TODAY,
                })
                url = (
                    "https://fred.stlouisfed.org/graph/fredgraph.csv?"
                    + params
                )

                payload = fetch_bytes(url)
                csv_text = payload.decode("utf-8-sig")

                if "observation_date" not in csv_text[:500].lower():
                    raise ValueError("Unexpected FRED CSV response")

                atomic_write(raw_path, payload)

                manifest.record_file(
                    raw_path,
                    "fred",
                    f"fred_{series}",
                    "FRED graph CSV download",
                    {"series_id": series, "start_date": START_DATE},
                )

            reader = csv.DictReader(io.StringIO(csv_text))

            if not reader.fieldnames:
                raise ValueError("CSV has no header")

            date_key = next(
                (
                    field for field in reader.fieldnames
                    if field.strip().lower() in {
                        "observation_date", "date"
                    }
                ),
                None,
            )

            value_key = next(
                (
                    field for field in reader.fieldnames
                    if field.strip() == series
                ),
                None,
            )

            if not date_key or not value_key:
                raise ValueError(
                    f"Missing expected CSV columns: {reader.fieldnames}"
                )

            target_group = groups.get(series, "macro")
            count = 0

            for row in reader:
                observation_date = (row.get(date_key) or "").strip()
                raw_value = (row.get(value_key) or "").strip()

                if not observation_date:
                    continue

                try:
                    date.fromisoformat(observation_date)
                except ValueError:
                    continue

                value = None

                if raw_value not in {"", "."}:
                    try:
                        parsed = float(raw_value)
                        if math.isfinite(parsed):
                            value = parsed
                    except ValueError:
                        continue

                grouped_rows[target_group].append({
                    "series_id": series,
                    "date": observation_date,
                    "value": value,
                })
                count += 1

            print(f"{series}: {count} observations")
            successful += 1

        except Exception as exc:
            print(f"FRED ERROR {series}: {type(exc).__name__}: {exc}")
            failed.append(series)

    for group, rows in grouped_rows.items():
        if not rows:
            continue

        destination = (
            lake.silver / group / f"fred_{group}_observations.parquet"
        )

        write_parquet(
            pl.DataFrame(rows, infer_schema_length=None),
            destination,
        )

        manifest.record_file(
            destination,
            "fred",
            f"fred_{group}_observations",
            "Normalised FRED CSV data",
            {"rows": len(rows), "start_date": START_DATE},
        )

        print(f"{group} Parquet rows: {len(rows)}")

    print("FRED series successful:", successful)
    print("FRED series failed:", failed)

    return sum(len(rows) for rows in grouped_rows.values())


def acquire_prices() -> int:
    print("\n========== OPENBB / CBOE DAILY PRICES ==========")

    try:
        from lqie.data.providers.openbb_cboe import OpenBBCBOEAdapter
        adapter = OpenBBCBOEAdapter()
    except Exception as exc:
        print("OpenBB adapter unavailable:", repr(exc))
        return 0

    price_rows = []
    downloaded = 0
    failed = []

    for symbol in MARKET_SYMBOLS:
        raw_path = (
            lake.bronze / "us" / "market" / "eod" / f"{symbol}.json"
        )

        try:
            if is_fresh(raw_path, 24):
                records = load_json(raw_path)
                print(f"Cached: {symbol} ({len(records)} rows)")
            else:
                bars = adapter.fetch_ohlcv(
                    symbol,
                    START_DATE,
                    TODAY,
                )

                records = []

                for bar in bars:
                    item = asdict(bar)
                    item["date"] = item["date"].isoformat()
                    item["retrieved_at_utc"] = (
                        item["retrieved_at_utc"].isoformat()
                    )
                    records.append(item)

                atomic_write(
                    raw_path,
                    json.dumps(records, separators=(",", ":")).encode(),
                )

                manifest.record_file(
                    raw_path,
                    "cboe",
                    f"daily_ohlcv_{symbol}",
                    "OpenBB CBOE historical provider",
                    {"symbol": symbol, "interval": "1d"},
                )

                downloaded += 1
                print(f"Downloaded: {symbol} ({len(records)} rows)")

            price_rows.extend(records)

        except Exception as exc:
            print(f"PRICE ERROR {symbol}: {type(exc).__name__}: {exc}")
            failed.append(symbol)

    if price_rows:
        destination = (
            lake.silver / "prices" / "daily" / "cboe_ohlcv.parquet"
        )

        write_parquet(
            pl.DataFrame(price_rows, infer_schema_length=None),
            destination,
        )

        manifest.record_file(
            destination,
            "cboe",
            "daily_equity_ohlcv",
            "Normalised OpenBB CBOE records",
            {"symbols": MARKET_SYMBOLS, "rows": len(price_rows)},
        )

        print("Total daily price observations:", len(price_rows))
        print("Price Parquet:", destination)

    print("Symbols downloaded:", downloaded)
    print("Symbols failed:", failed)

    return len(price_rows)


def main() -> None:
    print("LIONARE LQIE 0.4 — COMPACT DATA ACQUISITION")
    print("Data lake:", lake.root)
    print("Date:", TODAY)
    print("Initial history:", START_DATE, "to", TODAY)

    register_sources()

    sec_count = acquire_sec()
    fred_count = acquire_fred()
    price_count = acquire_prices()

    total_files = [
        path for path in lake.root.rglob("*")
        if path.is_file()
    ]

    total_bytes = sum(path.stat().st_size for path in total_files)

    print("\n========== ACQUISITION SUMMARY ==========")
    print("SEC fundamental observations:", sec_count)
    print("FRED observations:", fred_count)
    print("Daily market observations:", price_count)
    print("Total files in data lake:", len(total_files))
    print(f"Total data lake size: {total_bytes / 1024 / 1024:.2f} MB")

    print("\nRegistered sources:", len(registry.list_sources()))
    print("Manifest entries:", len(manifest.entries()))

    print("\nAcquisition completed. Check individual source errors above.")


if __name__ == "__main__":
    main()
