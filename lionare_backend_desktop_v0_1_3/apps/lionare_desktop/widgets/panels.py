from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from PySide6.QtCore import Qt, Signal, QUrl
from PySide6.QtGui import QColor, QDesktopServices, QFont, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..config import FUNDAMENTAL_METRICS, GLOBAL_MARKETS, WATCHLIST


def _text(value: Any, fallback: str = "—") -> str:
    if value is None or value == "":
        return fallback
    if isinstance(value, (dict, list)):
        return json.dumps(value, default=str, ensure_ascii=False)[:180]
    return str(value)


def _extract_list(payload: Any, keys: tuple[str, ...]) -> list[Any]:
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in keys:
            value = payload.get(key)
            if isinstance(value, list):
                return value
    return []


def _format_bytes(value: Any) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return _text(value)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if number < 1024 or unit == "TB":
            return f"{number:,.1f} {unit}"
        number /= 1024
    return f"{number:,.1f} TB"


def _format_metric(record: Any) -> str:
    if record is None:
        return "—"
    if isinstance(record, dict):
        value = record.get("usd_millions")
        year = record.get("year")
        if value is None:
            value = record.get("value")
            unit = record.get("unit")
            try:
                amount = float(value)
                if unit == "USD":
                    amount /= 1_000_000
                else:
                    return f"{amount:,.2f} {unit or ''}".strip()
            except (TypeError, ValueError):
                return _text(value)
        try:
            amount = float(value)
            if abs(amount) >= 1_000_000:
                formatted = f"${amount / 1_000_000:,.2f}T"
            elif abs(amount) >= 1_000:
                formatted = f"${amount / 1_000:,.2f}B"
            else:
                formatted = f"${amount:,.2f}M"
            return f"{formatted}  ·  FY {year}" if year else formatted
        except (TypeError, ValueError):
            return _text(value)
    try:
        return f"${float(record):,.2f}"
    except (TypeError, ValueError):
        return _text(record)


def _human_count(value: Any) -> str:
    try:
        return f"{int(value):,}"
    except (TypeError, ValueError):
        return _text(value)


class Panel(QWidget):
    """Content region for one dock. The dock title supplies the panel heading."""

    def __init__(self, subtitle: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("panelBody")
        self.setMinimumHeight(100)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(10, 7, 10, 10)
        self.layout.setSpacing(7)
        meta_row = QHBoxLayout()
        meta_row.addStretch(1)
        self.status_label = QLabel(subtitle.upper())
        self.status_label.setObjectName("panelMeta")
        meta_row.addWidget(self.status_label)
        self.layout.addLayout(meta_row)
        self.content_layout = QVBoxLayout()
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(7)
        self.layout.addLayout(self.content_layout, 1)

    def set_meta(self, text: str) -> None:
        self.status_label.setText(text.upper())

    def add_note(self, text: str, object_name: str = "mutedText") -> QLabel:
        label = QLabel(text)
        label.setObjectName(object_name)
        label.setWordWrap(True)
        self.content_layout.addWidget(label)
        return label


class SimpleTablePanel(Panel):
    def __init__(self, headers: list[str], rows: list[list[str]], subtitle: str = "") -> None:
        super().__init__(subtitle)
        self.table = QTableWidget(0, len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.setWordWrap(False)
        self.table.setHorizontalScrollMode(QTableWidget.ScrollMode.ScrollPerPixel)
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.table.setMinimumHeight(110)
        self.content_layout.addWidget(self.table)
        self.set_rows(rows)

    def set_rows(self, rows: list[list[str]]) -> None:
        self.table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            for column, value in enumerate(row):
                item = QTableWidgetItem(_text(value))
                item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
                self.table.setItem(row_index, column, item)
        self.table.resizeColumnsToContents()
        header = self.table.horizontalHeader()
        header.setStretchLastSection(True)


class GlobalMarketsPanel(SimpleTablePanel):
    def __init__(self) -> None:
        rows = [[name, region, "—", "NO QUOTE FEED"] for name, region in GLOBAL_MARKETS]
        super().__init__(["INDEX", "REGION", "LAST", "STATUS"], rows, "REFERENCE LIST · NO LIVE QUOTES")
        self.table.setColumnWidth(0, 125)
        self.table.setColumnWidth(1, 105)
        self.table.setColumnWidth(2, 65)


class WatchlistPanel(SimpleTablePanel):
    def __init__(self) -> None:
        rows = [[symbol, name, "—"] for symbol, name in WATCHLIST]
        super().__init__(["SYMBOL", "COMPANY", "LATEST FY REVENUE"], rows, "10 COMPANIES · SEC FUNDAMENTALS")
        self.table.setColumnWidth(0, 76)
        self.table.setColumnWidth(1, 180)

    def update_companies(self, payload: Any) -> None:
        records = _extract_list(payload, ("companies", "items", "results", "data"))
        if not records:
            self.set_meta("NO COMPANY RECORDS RETURNED")
            return
        rows: list[list[str]] = []
        for record in records:
            if not isinstance(record, dict):
                continue
            symbol = _text(record.get("symbol") or record.get("ticker"))
            company = _text(record.get("name") or record.get("company"))
            revenue = _format_metric(record.get("revenue_latest"))
            rows.append([symbol, company, revenue])
        if rows:
            self.set_rows(rows)
            self.set_meta(f"{len(rows)} COMPANIES · REPORTED FUNDAMENTALS · NO PRICE FEED")


class CompanyResearchPanel(Panel):
    symbol_changed = Signal(str)

    def __init__(self) -> None:
        super().__init__("SEC FUNDAMENTALS · ANNUAL")
        self.selector = QComboBox()
        for symbol, name in WATCHLIST:
            self.selector.addItem(f"{symbol}   ·   {name}", symbol)
        self.selector.currentIndexChanged.connect(self._selection_changed)
        self.content_layout.addWidget(self.selector)
        self.company_name = QLabel("Select a company")
        self.company_name.setObjectName("companyName")
        self.content_layout.addWidget(self.company_name)
        self.company_meta = self.add_note("Awaiting SEC fundamentals", "mutedText")

        grid = QGridLayout()
        grid.setHorizontalSpacing(7)
        grid.setVerticalSpacing(7)
        self.metric_labels: dict[str, QLabel] = {}
        captions = (
            ("revenue", "LATEST ANNUAL REVENUE"),
            ("net_income", "LATEST NET INCOME"),
            ("assets", "TOTAL ASSETS"),
            ("coverage", "HISTORICAL COVERAGE"),
        )
        for index, (key, caption) in enumerate(captions):
            wrapper = QFrame()
            wrapper.setObjectName("metricBlock")
            box = QVBoxLayout(wrapper)
            box.setContentsMargins(9, 7, 9, 7)
            box.setSpacing(4)
            caption_label = QLabel(caption)
            caption_label.setObjectName("metricCaption")
            value_label = QLabel("—")
            value_label.setWordWrap(True)
            value_label.setObjectName("metricValue")
            value_label.setFont(QFont("Consolas", 10, QFont.Weight.DemiBold))
            box.addWidget(caption_label)
            box.addWidget(value_label)
            grid.addWidget(wrapper, index // 2, index % 2)
            self.metric_labels[key] = value_label
        self.content_layout.addLayout(grid)

        self.forecast_heading = self.add_note("FUNDAMENTAL TREND FORECAST · NOT SHARE-PRICE FORECAST", "panelMeta")
        self.forecast_summary = self.add_note("Waiting for forecast service…")
        self.forecast_warning = self.add_note("Forecasts are experimental and are not investment recommendations.", "warnText")
        self._initial_signal_emitted = False
        self._selection_changed()

    def _selection_changed(self, *_: Any) -> None:
        symbol = str(self.selector.currentData() or "AAPL")
        self.company_meta.setText(f"{symbol} · REQUESTING COMPANY DATA")
        self.symbol_changed.emit(symbol)

    def update_company(self, payload: Any) -> None:
        if not isinstance(payload, dict):
            self.company_meta.setText("Unexpected company response")
            return
        record = payload
        for key in ("company", "data", "result"):
            if isinstance(payload.get(key), dict):
                record = payload[key]
                break
        symbol = _text(record.get("symbol") or record.get("ticker"), str(self.selector.currentData() or "AAPL"))
        name = _text(record.get("name") or record.get("company_name"), symbol)
        sector = _text(record.get("sector") or record.get("industry"), "SEC XBRL")
        self.company_name.setText(name)
        self.company_meta.setText(f"{symbol}  ·  {sector}  ·  REPORTED FUNDAMENTALS, NOT MARKET PRICE")
        self.metric_labels["revenue"].setText(_format_metric(record.get("revenue_latest")))
        self.metric_labels["net_income"].setText(_format_metric(record.get("net_income_latest")))
        self.metric_labels["assets"].setText(_format_metric(record.get("assets_latest")))
        metrics = record.get("metrics") if isinstance(record.get("metrics"), dict) else {}
        revenue_series = metrics.get("revenue") if isinstance(metrics.get("revenue"), list) else []
        years = record.get("revenue_years") or len(revenue_series)
        start, end = record.get("history_start"), record.get("history_end")
        coverage = f"{years} FYs"
        if start and end:
            coverage += f"  ·  {start}–{end}"
        self.metric_labels["coverage"].setText(coverage)

    def update_forecast(self, payload: Any) -> None:
        if not isinstance(payload, dict):
            return
        forecasts = payload.get("forecasts") if isinstance(payload.get("forecasts"), list) else []
        method = _text(payload.get("method"), "Experimental model")
        r2 = payload.get("r_squared")
        values = []
        for item in forecasts:
            if isinstance(item, dict):
                year = item.get("year") or item.get("forecast_year")
                value = item.get("value_usd")
                if value is None:
                    value = item.get("value") or item.get("forecast")
                if value is None:
                    value = item.get("usd_millions")
                    if value is not None:
                        value = float(value) * 1_000_000
                try:
                    text = f"FY {year}: ${float(value) / 1_000_000_000:,.2f}B"
                except (TypeError, ValueError):
                    text = f"FY {year}: {_text(value)}"
                values.append(text)
        self.forecast_summary.setText("   ·   ".join(values) if values else "No forecast values returned.")
        detail = f"{method} · R² {_text(r2)} · {payload.get('observations_used', '—')} observations"
        self.forecast_heading.setText(detail.upper())
        self.forecast_warning.setText(_text(payload.get("warning"), "Experimental historical fundamental trend; not a share-price forecast."))

    def set_error(self, message: str) -> None:
        self.company_meta.setText("Company API error: " + message[:240])


class MarketPulsePanel(Panel):
    def __init__(self) -> None:
        super().__init__("AWAITING VERIFIED PRICE DATA")
        self.value = self.add_note("Market breadth and sentiment are not available yet.", "warnText")
        self.add_note("A permitted market-price feed is required before these statistics can be calculated.")


class PortfolioPanel(Panel):
    def __init__(self) -> None:
        super().__init__("NO PORTFOLIO")
        self.add_note("No portfolio has been configured.", "warnText")
        self.add_note("Holdings, exposure, daily P&L and returns require saved positions and validated prices.")


class PerformancePanel(Panel):
    def __init__(self) -> None:
        super().__init__("DATA SOURCE PENDING")
        self.add_note("No verified market-price history is connected.", "warnText")
        self.add_note("Performance metrics remain unavailable until a permitted OHLCV source is integrated.")


class NewsPanel(Panel):
    def __init__(self) -> None:
        super().__init__("OFFICIAL HEADLINES · GDELT EVENTS")
        self.tabs = QTabWidget()
        self.headlines = QListWidget()
        self.events = QListWidget()
        self.tabs.addTab(self.headlines, "OFFICIAL HEADLINES")
        self.tabs.addTab(self.events, "GDELT EVENTS")
        self.content_layout.addWidget(self.tabs)
        self.headlines.itemDoubleClicked.connect(self._open_item)
        self.events.itemDoubleClicked.connect(self._open_item)
        self.headlines.addItem("Waiting for official feeds…")
        self.events.addItem("Waiting for GDELT feed…")

    @staticmethod
    def _open_item(item: QListWidgetItem) -> None:
        url = item.data(Qt.ItemDataRole.UserRole)
        if url:
            QDesktopServices.openUrl(QUrl(str(url)))

    def _populate(self, widget: QListWidget, records: list[Any], kind: str) -> None:
        widget.clear()
        if not records:
            widget.addItem(f"No {kind.lower()} returned by backend.")
            return
        for record in records[:150]:
            if isinstance(record, dict):
                title = _text(record.get("title") or record.get("headline") or record.get("name"), "Untitled item")
                source = _text(record.get("source") or record.get("publisher") or record.get("domain"), kind)
                published = _text(record.get("published") or record.get("published_at") or record.get("date") or record.get("datetime"), "")
                item = QListWidgetItem(f"{title}\n{source}  ·  {published}")
                url = record.get("url") or record.get("link") or record.get("documentidentifier")
                if url and str(url).startswith(("http://", "https://")):
                    item.setData(Qt.ItemDataRole.UserRole, str(url))
            else:
                item = QListWidgetItem(_text(record))
            widget.addItem(item)

    def update_news(self, payload: Any) -> None:
        headlines = payload.get("headlines", []) if isinstance(payload, dict) else _extract_list(payload, ("news", "items", "articles", "results", "data"))
        events = payload.get("events", []) if isinstance(payload, dict) and isinstance(payload.get("events"), list) else []
        if not isinstance(headlines, list):
            headlines = []
        self._populate(self.headlines, headlines, "OFFICIAL HEADLINES")
        self._populate(self.events, events, "GDELT EVENTS")
        self.set_meta(f"{len(headlines)} OFFICIAL HEADLINES · {len(events)} GDELT EVENTS")

    def set_error(self, message: str) -> None:
        self._populate(self.headlines, [], "OFFICIAL HEADLINES")
        self.headlines.insertItem(0, "NEWS SERVICE ERROR: " + message[:220])
        self.set_meta("REQUEST ERROR")


class QuantPanel(Panel):
    def __init__(self, lqie_available: bool, trendline_status: str) -> None:
        super().__init__("LQIE ENGINE · ARCHIVED RUNS")
        self.engine_label = self.add_note(f"LQIE package: {'AVAILABLE' if lqie_available else 'NOT FOUND'}", "goodText" if lqie_available else "warnText")
        self.version_label = self.add_note("Pattern engine: 0.5.0", "mutedText")
        self.status_label_detail = self.add_note(f"Trendlines: {trendline_status}", "warnText")
        self.summary = self.add_note("Waiting for LQIE status endpoint…")
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["RUN", "SYMBOL", "TF", "STATUS", "BARS", "DETECTIONS"])
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.content_layout.addWidget(self.table, 1)
        self.add_note("Analysis stays in the backend process; this panel is read-only.")

    def update_status(self, payload: Any) -> None:
        if not isinstance(payload, dict):
            return
        available = bool(payload.get("engine_available", False))
        version = _text(payload.get("engine_version"), "unknown")
        count = payload.get("run_count", 0)
        output_count = payload.get("gold_output_count", 0)
        self.engine_label.setText(f"LQIE package: {'AVAILABLE' if available else 'NOT FOUND'}")
        self.engine_label.setObjectName("goodText" if available else "warnText")
        self.engine_label.style().unpolish(self.engine_label)
        self.engine_label.style().polish(self.engine_label)
        self.version_label.setText(f"Pattern engine: {version}")
        latest = payload.get("latest_run") if isinstance(payload.get("latest_run"), dict) else None
        if latest:
            self.summary.setText(
                f"{count} archived runs · {output_count} Gold outputs · latest {latest.get('symbol', '—')} "
                f"{latest.get('started_utc', '')} · {latest.get('status', 'unknown')}"
            )
        else:
            self.summary.setText(f"{count} archived runs · {output_count} Gold outputs · no archived run index yet")
        compat = payload.get("trendline_compatibility")
        if isinstance(compat, dict):
            state = compat.get("status", "not_checked")
            self.status_label_detail.setText(f"Trendline compatibility: {state}")
            self.status_label_detail.setObjectName("warnText" if state == "compatibility_warning" else "mutedText")
            self.status_label_detail.style().unpolish(self.status_label_detail)
            self.status_label_detail.style().polish(self.status_label_detail)

    def update_runs(self, payload: Any) -> None:
        runs = _extract_list(payload, ("runs", "items", "results"))
        self.table.setRowCount(min(len(runs), 100))
        for row, record in enumerate(runs[:100]):
            if not isinstance(record, dict):
                continue
            values = [
                _text(record.get("run_id")),
                _text(record.get("symbol")),
                _text(record.get("timeframe")),
                _text(record.get("status")),
                _human_count(record.get("bars_analysed")),
                _human_count(record.get("pattern_detections")),
            ]
            for col, value in enumerate(values):
                self.table.setItem(row, col, QTableWidgetItem(value))
        self.table.resizeColumnsToContents()


class DataLakePanel(Panel):
    def __init__(self) -> None:
        super().__init__("BRONZE · SILVER · GOLD · CATALOG")
        self.summary = self.add_note("Waiting for data lake overview…")
        self.updated = self.add_note("Last fundamentals update: —", "panelMeta")
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["DATASET / VIEW", "ROWS", "SIZE", "DETAILS"])
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.content_layout.addWidget(self.table, 1)

    def update_overview(self, payload: Any) -> None:
        if not isinstance(payload, dict):
            return
        total = payload.get("storage_bytes")
        datasets = payload.get("datasets")
        records = _extract_list(datasets, ("datasets", "items", "results"))
        company_count = payload.get("company_count", "—")
        version = payload.get("version", "—")
        if total is not None:
            self.summary.setText(f"{len(records)} DATASETS · {_format_bytes(total)} TOTAL STORAGE · {company_count} COMPANIES · DATA SERVICE {version}")
        else:
            self.summary.setText(f"{len(records)} DATASETS · {company_count} COMPANIES · DATA SERVICE {version}")
        self.updated.setText("Last fundamentals update: " + _text(payload.get("last_fundamentals_update")))
        rows: list[list[str]] = []
        for record in records[:250]:
            if isinstance(record, dict):
                name = next((record.get(k) for k in ("name", "dataset", "view", "table", "dataset_name", "path") if record.get(k) not in (None, "")), "Unknown dataset")
                row_count = next((record.get(k) for k in ("rows", "row_count", "records", "count", "num_rows") if record.get(k) is not None), "—")
                size = next((record.get(k) for k in ("size", "size_bytes", "bytes", "file_size") if record.get(k) is not None), None)
                details = []
                for key in ("layer", "columns", "source", "format", "path"):
                    if record.get(key) not in (None, "") and str(record.get(key)) != str(name):
                        details.append(f"{key}: {_text(record[key])}")
                rows.append([_text(name), _human_count(row_count), _format_bytes(size) if size is not None else "—", " · ".join(details)[:160]])
            else:
                rows.append([_text(record), "—", "—", ""])
        self._set_rows(rows)

    def _set_rows(self, rows: list[list[str]]) -> None:
        self.table.setRowCount(len(rows))
        for row, values in enumerate(rows):
            for col, value in enumerate(values):
                self.table.setItem(row, col, QTableWidgetItem(value))
        self.table.resizeColumnsToContents()
        self.table.setColumnWidth(0, 280)
        self.table.setColumnWidth(1, 85)
        self.table.setColumnWidth(2, 100)


class SystemPanel(Panel):
    def __init__(self, api_url: str) -> None:
        super().__init__("LOCAL NODE · SOURCE MONITOR")
        self.backend = self.add_note("Backend: CHECKING…", "warnText")
        self.backend_url = self.add_note(f"API endpoint: {api_url}")
        self.storage = self.add_note("Data lake: provided by backend overview")
        self.last_update = self.add_note("Last update: —", "panelMeta")
        self.health = self.add_note("Source monitor: awaiting backend", "mutedText")
        self.source_details = self.add_note("Probe / RSS / GDELT details pending", "mutedText")

    def set_backend(self, online: bool, detail: str = "") -> None:
        self.backend.setText(f"Backend: {'ONLINE' if online else 'OFFLINE'}" + (f"  ·  {detail}" if detail else ""))
        self.backend.setObjectName("goodText" if online else "warnText")
        self.backend.style().unpolish(self.backend)
        self.backend.style().polish(self.backend)
        self.last_update.setText("Last update: " + datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z"))

    @staticmethod
    def _count_ok(records: list[Any]) -> tuple[int, int]:
        ok = 0
        for record in records:
            if not isinstance(record, dict):
                continue
            status = str(record.get("status", "")).lower()
            if status in {"ok", "healthy", "online", "success", "available", "200"}:
                ok += 1
        return ok, len(records)

    def update_health(self, payload: Any) -> None:
        if not isinstance(payload, dict):
            return
        probes = payload.get("probe_results") if isinstance(payload.get("probe_results"), list) else []
        rss = payload.get("rss_results") if isinstance(payload.get("rss_results"), list) else []
        gdelt = payload.get("gdelt_result") if isinstance(payload.get("gdelt_result"), dict) else {}
        probe_ok, probe_total = self._count_ok(probes)
        rss_ok, rss_total = self._count_ok(rss)
        gdelt_status = _text(gdelt.get("status"), "unknown").upper()
        self.health.setText(
            f"Source monitor checked: {_text(payload.get('checked_at_utc'))} · "
            f"PROBES {probe_ok}/{probe_total} · RSS {rss_ok}/{rss_total} · GDELT {gdelt_status}"
        )
        failed = [
            _text(item.get("source") or item.get("name") or item.get("url"), "source")
            + ": " + _text(item.get("status"), "unknown")
            for item in probes + rss
            if isinstance(item, dict) and str(item.get("status", "")).lower() not in {"ok", "healthy", "online", "success", "available", "200"}
        ]
        if gdelt and str(gdelt.get("status", "")).lower() not in {"ok", "healthy", "online", "success", "available", "200"}:
            failed.append("GDELT: " + gdelt_status)
        self.source_details.setText("Issues: " + " · ".join(failed[:8]) if failed else "No failed source statuses reported in the latest health snapshot.")


class ChartWorkspace(QFrame):
    """Displays reported SEC fundamentals; never labels them as market prices."""

    metric_changed = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("chartWorkspace")
        self.current_symbol = "AAPL"
        self.current_metric = "revenue"
        self.current_records: list[dict[str, Any]] = []
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 13, 16, 13)
        layout.setSpacing(9)

        top = QHBoxLayout()
        title_box = QVBoxLayout()
        title = QLabel("MARKET WORKSPACE")
        title.setObjectName("chartTitle")
        self.subtitle = QLabel("GLOBAL OVERVIEW · REFERENCE DATA ONLY")
        self.subtitle.setObjectName("chartSubtitle")
        title_box.addWidget(title)
        title_box.addWidget(self.subtitle)
        top.addLayout(title_box)
        top.addStretch(1)
        self.metric_combo = QComboBox()
        for key, label in FUNDAMENTAL_METRICS:
            self.metric_combo.addItem(label, key)
        self.metric_combo.currentIndexChanged.connect(self._metric_selected)
        top.addWidget(QLabel("FUNDAMENTAL:"))
        top.addWidget(self.metric_combo)
        self.instrument = QLabel("AAPL · REVENUE · SEC ANNUAL")
        self.instrument.setObjectName("panelMeta")
        top.addWidget(self.instrument)
        layout.addLayout(top)

        self.canvas = ChartCanvas()
        layout.addWidget(self.canvas, 1)
        bottom = QHBoxLayout()
        note = QLabel("REPORTED FINANCIAL FUNDAMENTALS · NOT STOCK PRICES")
        note.setObjectName("warnText")
        bottom.addWidget(note)
        bottom.addStretch(1)
        self.data_state = QLabel("WAITING FOR API DATA")
        self.data_state.setObjectName("panelMeta")
        bottom.addWidget(self.data_state)
        layout.addLayout(bottom)

    def _metric_selected(self, *_: Any) -> None:
        self.current_metric = str(self.metric_combo.currentData() or "revenue")
        self.metric_changed.emit(self.current_metric)

    def set_workspace(self, name: str) -> None:
        subtitles = {
            "DASHBOARD": "COMPANY FUNDAMENTALS · MARKET FEED NOT CONNECTED",
            "MARKETS": "GLOBAL MARKETS · VERIFIED QUOTE FEED NOT CONNECTED",
            "EQUITY": "EQUITY RESEARCH · REPORTED SEC FINANCIALS",
            "PORTFOLIO": "PORTFOLIO MONITOR · NO SAVED POSITIONS",
            "NEWS": "NEWS & EVENTS · OFFICIAL HEADLINES + GDELT",
            "QUANT LAB": "LQIE RESEARCH · QUANTITATIVE RUN HISTORY",
            "DATA LAKE": "DATASETS · BRONZE / SILVER / GOLD",
            "SYSTEM": "ENGINE HEALTH · SOURCE MONITOR",
        }
        self.subtitle.setText(subtitles.get(name, name))

    def set_series(self, payload: Any, symbol: str, metric: str) -> None:
        records: list[dict[str, Any]] = []
        if isinstance(payload, dict):
            series = payload.get("series")
            if isinstance(series, list) and series and isinstance(series[0], dict):
                data = series[0].get("data")
                if isinstance(data, list):
                    records = [item for item in data if isinstance(item, dict)]
        self.current_symbol = symbol
        self.current_metric = metric
        self.current_records = records
        label = payload.get("label", metric.replace("_", " ").title()) if isinstance(payload, dict) else metric
        self.instrument.setText(f"{symbol} · {str(label).upper()} · SEC ANNUAL")
        self.data_state.setText(f"{len(records)} ANNUAL OBSERVATIONS" if records else "NO SERIES DATA")
        self.canvas.set_series(records, str(label), symbol)

    def set_error(self, message: str) -> None:
        self.data_state.setText("API ERROR · " + message[:100])


class ChartCanvas(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("chartCanvasFrame")
        self.setMinimumSize(400, 300)
        self.records: list[dict[str, Any]] = []
        self.metric_label = "fundamental"
        self.symbol = "AAPL"

    def set_series(self, records: list[dict[str, Any]], metric_label: str, symbol: str) -> None:
        self.records = records
        self.metric_label = metric_label
        self.symbol = symbol
        self.update()

    def paintEvent(self, event: Any) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect().adjusted(54, 22, -24, -42)
        painter.fillRect(self.rect(), QColor("#080e15"))
        painter.setPen(QPen(QColor("#1b2b3b"), 1))
        for i in range(6):
            y = rect.top() + int(rect.height() * i / 5)
            painter.drawLine(rect.left(), y, rect.right(), y)
        for i in range(9):
            x = rect.left() + int(rect.width() * i / 8)
            painter.drawLine(x, rect.top(), x, rect.bottom())

        points: list[tuple[int, float, float]] = []
        for record in self.records:
            try:
                year = float(record.get("year"))
                value = float(record.get("usd_millions", record.get("value")))
                if record.get("usd_millions") is None and record.get("unit") == "USD":
                    value /= 1_000_000
                if year == year and value == value:
                    points.append((int(year), value, float(record.get("value", value))))
            except (TypeError, ValueError):
                continue
        if len(points) < 2:
            painter.setPen(QColor("#68829a"))
            painter.setFont(QFont("Consolas", 10))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "WAITING FOR HISTORICAL FUNDAMENTALS\n\nNo share prices or synthetic candles are shown.")
            painter.end()
            return

        values = [p[1] for p in points]
        low, high = min(values), max(values)
        if high == low:
            high = low + 1
        x_min, x_max = min(p[0] for p in points), max(p[0] for p in points)
        if x_max == x_min:
            x_max += 1

        def xy(year: int, value: float) -> tuple[float, float]:
            x = rect.left() + (year - x_min) / (x_max - x_min) * rect.width()
            y = rect.bottom() - (value - low) / (high - low) * rect.height()
            return x, y

        path = QPainterPath()
        for index, (year, value, _raw) in enumerate(points):
            x, y = xy(year, value)
            if index == 0:
                path.moveTo(x, y)
            else:
                path.lineTo(x, y)
        painter.setPen(QPen(QColor("#43d6b0"), 2.3))
        painter.drawPath(path)
        painter.setBrush(QColor("#43d6b0"))
        painter.setPen(Qt.PenStyle.NoPen)
        for year, value, _raw in points:
            x, y = xy(year, value)
            painter.drawEllipse(int(x - 3), int(y - 3), 6, 6)

        painter.setPen(QColor("#8098ae"))
        painter.setFont(QFont("Consolas", 8))
        for idx, fraction in enumerate((0, .25, .5, .75, 1)):
            value = high - (high - low) * fraction
            y = rect.top() + int(rect.height() * fraction)
            painter.drawText(4, y + 4, f"${value:,.0f}M")
        painter.drawText(rect.left(), rect.bottom() + 25, str(x_min))
        painter.drawText(rect.right() - 35, rect.bottom() + 25, str(x_max))
        painter.drawText(8, 16, f"{self.symbol} · {self.metric_label} · {len(points)} FY observations")
        painter.end()
