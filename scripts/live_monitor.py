"""Live source health, official RSS and GDELT event monitor."""

import argparse
import csv
import io
import json
import os
import time
import zipfile
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

import polars as pl

from lqie.data.lake import LakePaths, write_parquet

lake = LakePaths().ensure()
SEC_EMAIL = os.environ.get("SEC_CONTACT_EMAIL", "").strip()

RSS_FEEDS = [
    ("BLS", "https://www.bls.gov/feed/bls_latest.rss"),
    ("Federal Reserve", "https://www.federalreserve.gov/feeds/press_all.xml"),
    ("RBI", "https://rbi.org.in/pressreleases_rss.xml"),
    ("PIB India", "https://pib.gov.in/RssMain.aspx?ModId=6&Lang=1&Regid=1"),
]

if SEC_EMAIL:
    RSS_FEEDS.append(
        ("SEC", "https://www.sec.gov/news/pressreleases.rss")
    )

PROBES = {
    "BLS API": "https://api.bls.gov/publicAPI/v1/timeseries/data/CUSR0000SA0",
    "World Bank": "https://api.worldbank.org/v2/country/USA/indicator/NY.GDP.MKTP.CD?format=json&per_page=1",
    "US Treasury": (
        "https://home.treasury.gov/resource-center/data-chart-center/"
        "interest-rates/pages/xml?data=daily_treasury_yield_curve"
        f"&field_tdr_date_value={datetime.now(timezone.utc).year}"
    ),
    "ECB FX": (
        "https://data-api.ecb.europa.eu/service/data/EXR/"
        "D.USD.EUR.SP00.A?lastNObservations=1&format=csvdata"
    ),
    "CFTC": "https://www.cftc.gov/MarketReports/CommitmentsofTraders/HistoricalCompressed/index.htm",
    "GDELT": "https://data.gdeltproject.org/gdeltv2/lastupdate.txt",
}

if SEC_EMAIL:
    PROBES["SEC"] = (
        "https://data.sec.gov/api/xbrl/companyfacts/CIK0000320193.json"
    )


def user_agent():
    if SEC_EMAIL:
        return f"Lionare LQIE/0.4 contact: {SEC_EMAIL}"
    return "Lionare LQIE/0.4 public-data monitor"


def fetch(url, timeout=30):
    request = Request(
        url,
        headers={
            "User-Agent": user_agent(),
            "Accept": "*/*",
        },
    )
    with urlopen(request, timeout=timeout) as response:
        return response.read()


def atomic_write(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".part")
    temp.write_bytes(payload)
    temp.replace(path)


def local_name(tag):
    return tag.rsplit("}", 1)[-1].split(":")[-1]


def child_text(element, names):
    for child in element:
        if local_name(child.tag) in names:
            value = "".join(child.itertext()).strip()
            if value:
                return value
            if child.attrib.get("href"):
                return child.attrib["href"]
    return ""


def refresh_rss():
    print("\n========== OFFICIAL NEWS FEEDS ==========")
    rows = []
    statuses = []

    for source, url in RSS_FEEDS:
        try:
            payload = fetch(url)
            raw_path = (
                lake.bronze / "global" / "news"
                / (source.lower().replace(" ", "_") + ".xml")
            )
            atomic_write(raw_path, payload)

            root = ET.fromstring(payload)
            feed_count = 0

            for item in root.iter():
                if local_name(item.tag) not in {"item", "entry"}:
                    continue

                title = child_text(item, {"title"})
                link = child_text(item, {"link", "guid"})
                published = child_text(
                    item, {"pubDate", "published", "updated", "date"}
                )

                if not title or not link:
                    continue

                rows.append({
                    "source": source,
                    "title": title,
                    "link": link,
                    "published_at": published,
                    "collected_at_utc": datetime.now(
                        timezone.utc
                    ).isoformat(),
                })
                feed_count += 1

            statuses.append({
                "source": source,
                "status": "UP",
                "items_found": feed_count,
            })
            print(f"{source}: {feed_count} headlines")

        except Exception as exc:
            statuses.append({
                "source": source,
                "status": "ERROR",
                "error": f"{type(exc).__name__}: {exc}",
            })
            print(f"{source} ERROR: {type(exc).__name__}: {exc}")

    if rows:
        destination = lake.silver / "news" / "official_headlines.parquet"
        new_frame = pl.DataFrame(rows, infer_schema_length=None)

        if destination.is_file():
            old_frame = pl.read_parquet(destination)
            new_frame = pl.concat(
                [old_frame, new_frame],
                how="diagonal_relaxed",
            )

        new_frame = (
            new_frame
            .unique(subset=["link"], keep="last", maintain_order=True)
            .tail(1500)
        )

        write_parquet(new_frame, destination)
        print("Stored headline records:", new_frame.height)

    return statuses


def refresh_gdelt():
    print("\n========== GDELT 15-MINUTE EVENT STREAM ==========")

    try:
        heartbeat = fetch(
            "https://data.gdeltproject.org/gdeltv2/lastupdate.txt"
        ).decode("utf-8", errors="replace")

        export_url = None

        for line in heartbeat.splitlines():
            parts = line.split()
            if parts and "export.CSV.zip" in parts[-1]:
                export_url = parts[-1]
                break

        if not export_url:
            raise RuntimeError("No GDELT event export URL in lastupdate.txt")

        payload = fetch(export_url)

        if not payload.startswith(b"PK"):
            raise ValueError("GDELT event response is not a ZIP archive")

        raw_path = (
            lake.bronze / "global" / "gdelt" / "gdelt_latest_export.zip"
        )
        atomic_write(raw_path, payload)

        rows = []

        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            members = [
                name for name in archive.namelist()
                if name.lower().endswith(".csv")
            ]

            if not members:
                raise ValueError("No CSV member found in GDELT ZIP")

            text = archive.read(members[0]).decode(
                "utf-8", errors="replace"
            )

            reader = csv.reader(io.StringIO(text), delimiter="\t")

            for event in reader:
                if len(event) < 58:
                    continue

                rows.append({
                    "event_id": event[0],
                    "event_day": event[1],
                    "actor1_name": event[6],
                    "actor2_name": event[16],
                    "event_code": event[26],
                    "event_root_code": event[28],
                    "quad_class": event[29],
                    "goldstein_scale": event[30],
                    "num_mentions": event[31],
                    "num_sources": event[32],
                    "num_articles": event[33],
                    "average_tone": event[34],
                    "action_location": event[50],
                    "action_country_code": event[51],
                    "date_added": event[-2],
                    "source_url": event[-1],
                    "collected_at_utc": datetime.now(
                        timezone.utc
                    ).isoformat(),
                })

        if rows:
            destination = (
                lake.silver / "news" / "gdelt_events_latest.parquet"
            )
            write_parquet(
                pl.DataFrame(rows, infer_schema_length=None),
                destination,
            )

        heartbeat_path = (
            lake.metadata / "quality" / "gdelt_heartbeat.json"
        )
        atomic_write(
            heartbeat_path,
            json.dumps({
                "checked_at_utc": datetime.now(timezone.utc).isoformat(),
                "latest_export_url": export_url,
                "event_rows": len(rows),
                "archive_bytes": len(payload),
            }, indent=2).encode("utf-8"),
        )

        print("GDELT latest export:", export_url)
        print("GDELT event rows:", len(rows))

        return {
            "source": "GDELT",
            "status": "UP",
            "event_rows": len(rows),
            "latest_export_url": export_url,
        }

    except Exception as exc:
        print(f"GDELT ERROR: {type(exc).__name__}: {exc}")
        return {
            "source": "GDELT",
            "status": "ERROR",
            "error": f"{type(exc).__name__}: {exc}",
        }


def check_probes():
    print("\n========== SOURCE HEALTH CHECK ==========")
    results = []

    for source, url in PROBES.items():
        started = time.perf_counter()

        try:
            payload = fetch(url, timeout=25)
            elapsed_ms = round(
                (time.perf_counter() - started) * 1000, 1
            )

            results.append({
                "source": source,
                "status": "UP",
                "checked_at_utc": datetime.now(
                    timezone.utc
                ).isoformat(),
                "latency_ms": elapsed_ms,
                "response_bytes_sampled": len(payload),
                "url": url,
            })

            print(f"{source}: UP ({elapsed_ms} ms)")

        except Exception as exc:
            elapsed_ms = round(
                (time.perf_counter() - started) * 1000, 1
            )

            results.append({
                "source": source,
                "status": "ERROR",
                "checked_at_utc": datetime.now(
                    timezone.utc
                ).isoformat(),
                "latency_ms": elapsed_ms,
                "error": f"{type(exc).__name__}: {exc}",
                "url": url,
            })

            print(f"{source}: ERROR - {type(exc).__name__}: {exc}")

    return results


def run_once():
    checked_at = datetime.now(timezone.utc).isoformat()

    probe_results = check_probes()
    rss_results = refresh_rss()
    gdelt_result = refresh_gdelt()

    report = {
        "checked_at_utc": checked_at,
        "probe_results": probe_results,
        "rss_results": rss_results,
        "gdelt_result": gdelt_result,
    }

    destination = (
        lake.metadata / "quality" / "source_health.json"
    )
    atomic_write(
        destination,
        json.dumps(report, indent=2).encode("utf-8"),
    )

    up = sum(item["status"] == "UP" for item in probe_results)
    total = len(probe_results)

    print("\n========== HEALTH REPORT ==========")
    print(f"Reachable probes: {up}/{total}")
    print("Saved:", destination)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--watch",
        action="store_true",
        help="Repeat monitoring at the configured interval.",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=900,
        help="Seconds between refreshes (default: 900).",
    )
    args = parser.parse_args()

    if args.interval < 60:
        parser.error("Use an interval of at least 60 seconds.")

    if not args.watch:
        run_once()
        return

    print(f"Lionare live monitor running every {args.interval} seconds.")
    try:
        while True:
            run_once()
            print(f"\nNext refresh in {args.interval} seconds. Ctrl+C to stop.")
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\nLive monitor stopped.")


if __name__ == "__main__":
    main()
