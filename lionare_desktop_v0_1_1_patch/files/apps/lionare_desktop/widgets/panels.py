from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPainter, QPen, QColor, QFont
from PySide6.QtWidgets import (
    QFrame,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..config import DATA_LAKE_ROOT, GLOBAL_MARKETS, WATCHLIST


def _text(value: Any, fallback: str = "—") -> str:
    if value is None or value == "":
        return fallback
    if isinstance(value, (dict, list)):
        return str(value)
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


def _money_from_record(record: Any) -> str:
    if not isinstance(record, dict):
        return "—"
    value = record.get("usd_millions")
    if value is None:
        value = record.get("value")
        scale = 1_000_000
    else:
        scale = 1
    try:
        millions = float(value) / scale
    except (TypeError, ValueError):
        return "—"
    absolute = abs(millions)
    if absolute >= 1_000_000:
        return f"${millions / 1_000_000:,.2f}T"
    if absolute >= 1_000:
        return f"${millions / 1_000:,.2f}B"
    return f"${millions:,.1f}M"


class Panel(QWidget):
    def __init__(self, title: str, subtitle: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("panelBody")
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(10, 8, 10, 10)
        self.layout.setSpacing(7)
        heading = QHBoxLayout()
        self.title_label = QLabel(title.upper())
        self.title_label.setObjectName("panelHeading")
        heading.addWidget(self.title_label)
        heading.addStretch(1)
        self.status_label = QLabel(subtitle.upper())
        self.status_label.setObjectName("panelMeta")
        heading.addWidget(self.status_label)
        self.layout.addLayout(heading)
        self.content_layout = QVBoxLayout()
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(6)
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
    def __init__(self, title: str, headers: list[str], rows: list[list[str]], subtitle: str = "") -> None:
        super().__init__(title, subtitle)
        self.table = QTableWidget(len(rows), len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.content_layout.addWidget(self.table)
        self.set_rows(rows)

    def set_rows(self, rows: list[list[str]]) -> None:
        self.table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            for col_index, value in enumerate(row):
                item = QTableWidgetItem(_text(value))
                item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
                self.table.setItem(row_index, col_index, item)
        self.table.resizeColumnsToContents()


class GlobalMarketsPanel(SimpleTablePanel):
    def __init__(self) -> None:
        rows = [[name, region, "—", "FEED PENDING"] for name, region in GLOBAL_MARKETS]
        super().__init__("Global Markets", ["INDEX", "REGION", "LAST", "STATUS"], rows, "REFERENCE LIST · NO QUOTES")
        self.table.setColumnWidth(0, 135)
        self.table.setColumnWidth(1, 110)


class WatchlistPanel(SimpleTablePanel):
    def __init__(self) -> None:
        rows = [[symbol, name, "—", "AWAITING FUNDAMENTALS"] for symbol, name in WATCHLIST]
        super().__init__("Watchlist", ["SYMBOL", "COMPANY", "LAST", "DATA STATUS"], rows, "INITIAL COMPANY UNIVERSE")
        self.table.setColumnWidth(0, 70)
        self.table.setColumnWidth(1, 190)

    def update_companies(self, payload: Any) -> None:
        records = _extract_list(payload, ("companies", "items", "results", "data"))
        if not records:
            return
        rows: list[list[str]] = []
        for record in records:
            if isinstance(record, dict):
                symbol = _text(record.get("symbol") or record.get("ticker"))
                company = _text(record.get("name") or record.get("company"))
                status = "FUNDAMENTALS LOADED" if record.get("revenue_latest") or record.get("history_end") else "NO FUNDAMENTAL DATA"
            else:
                symbol, company, status = _text(record), "", "NO FUNDAMENTAL DATA"
            if symbol != "—":
                rows.append([symbol, company, "—", status])
        if rows:
            self.set_rows(rows)
            self.set_meta(f"{len(rows)} COMPANIES · PRICE FEED NOT CONNECTED")


class CompanyResearchPanel(Panel):
    symbol_changed = Signal(str)

    def __init__(self) -> None:
        super().__init__("Company Research", "SEC FUNDAMENTALS")
        self.selector = QComboBox()
        for symbol, name in WATCHLIST:
            self.selector.addItem(f"{symbol}  ·  {name}", symbol)
        self.selector.currentIndexChanged.connect(self._selection_changed)
        self.content_layout.addWidget(self.selector)
        self.company_name = self.add_note("Select a company", "goodText")
        self.company_meta = self.add_note("Awaiting SEC fundamentals")
        self.metric_labels: dict[str, QLabel] = {}
        for key, caption in (
            ("revenue", "LATEST ANNUAL REVENUE"),
            ("net_income", "LATEST NET INCOME"),
            ("assets", "TOTAL ASSETS"),
            ("coverage", "HISTORICAL COVERAGE"),
        ):
            block = QLabel(f"{caption}\n—")
            block.setObjectName("metricBlock")
            block.setWordWrap(True)
            self.content_layout.addWidget(block)
            self.metric_labels[key] = block

    def _selection_changed(self, *_: Any) -> None:
        symbol = str(self.selector.currentData() or "AAPL")
        self.company_meta.setText(f"{symbol} · REQUESTING COMPANY DATA")
        self.symbol_changed.emit(symbol)

    def set_error(self, message: str) -> None:
        self.company_meta.setText(f"COMPANY REQUEST FAILED · {message}")

    def update_company(self, payload: Any) -> None:
        # Exact response from server.py: company_summary() plus a metrics map
        # whose values are lists of annual SEC observation dictionaries.
        if not isinstance(payload, dict):
            self.company_meta.setText("Unexpected company response shape")
            return
        symbol = _text(payload.get("symbol"), str(self.selector.currentData() or "AAPL"))
        name = _text(payload.get("name"), symbol)
        sector = _text(payload.get("sector"), "SEC XBRL")
        self.company_name.setText(name)
        self.company_meta.setText(f"{symbol} · {sector} · SEC XBRL · ANNUAL FUNDAMENTALS")

        metric_records = {
            "revenue": payload.get("revenue_latest"),
            "net_income": payload.get("net_income_latest"),
            "assets": payload.get("assets_latest"),
        }
        captions = {
            "revenue": "LATEST ANNUAL REVENUE",
            "net_income": "LATEST NET INCOME",
            "assets": "TOTAL ASSETS",
        }
        for key, record in metric_records.items():
            if isinstance(record, dict):
                value = _money_from_record(record)
                year = _text(record.get("year"))
                self.metric_labels[key].setText(f"{captions[key]}\n{value}  ·  FY {year}")
            else:
                self.metric_labels[key].setText(f"{captions[key]}\n—")

        start = payload.get("history_start")
        end = payload.get("history_end")
        count = payload.get("revenue_years")
        if start is not None and end is not None:
            coverage = f"{start}–{end}  ·  {count or '—'} annual observations"
        else:
            coverage = "No annual revenue history available"
        self.metric_labels["coverage"].setText(f"HISTORICAL COVERAGE\n{coverage}")


class MarketPulsePanel(Panel):
    def __init__(self) -> None:
        super().__init__("Market Pulse", "WAITING FOR PRICE FEED")
        self.add_note("Market breadth and sentiment will appear when a validated market-price source is connected.")
        self.add_note("No synthetic or placeholder market statistics are displayed.")


class PortfolioPanel(Panel):
    def __init__(self) -> None:
        super().__init__("Portfolio Summary", "NO PORTFOLIO")
        self.add_note("No portfolio has been configured.")
        self.add_note("Holdings, exposure, daily P&L and total return require saved positions and permitted market prices.")


class PerformancePanel(Panel):
    def __init__(self) -> None:
        super().__init__("Performance Tracker", "DATA SOURCE PENDING")
        self.add_note("No verified live or historical market-price feed is connected.")
        self.add_note("Performance metrics will remain unavailable until price data is integrated.")


class NewsPanel(Panel):
    def __init__(self) -> None:
        super().__init__("News & Events", "OFFICIAL / INGESTED FEEDS")
        self.list_widget = QListWidget()
        self.content_layout.addWidget(self.list_widget)
        self.list_widget.addItem("Waiting for the existing Lionare news service…")

    def set_error(self, message: str) -> None:
        self.set_meta("REQUEST ERROR")
        self.list_widget.clear()
        self.list_widget.addItem(f"News request failed: {message}")

    def update_news(self, payload: Any) -> None:
        # Exact response from server.py: {"headlines": [...], "events": [...]}.
        if not isinstance(payload, dict):
            self.list_widget.clear()
            self.list_widget.addItem("Unexpected news response shape.")
            return
        headlines = payload.get("headlines") if isinstance(payload.get("headlines"), list) else []
        events = payload.get("events") if isinstance(payload.get("events"), list) else []
        self.list_widget.clear()

        combined: list[tuple[str, Any]] = [("NEWS", row) for row in headlines]
        combined.extend(("GDELT EVENT", row) for row in events)
        combined = combined[:100]
        if not combined:
            self.list_widget.addItem("No ingested headlines or GDELT events are currently available.")
            self.set_meta("0 ITEMS")
            return

        for kind, record in combined:
            if isinstance(record, dict):
                title = _text(
                    record.get("title")
                    or record.get("headline")
                    or record.get("name")
                    or record.get("event")
                    or record.get("url"),
                    "Untitled record",
                )
                source = _text(record.get("source") or record.get("domain") or record.get("publisher"), kind)
                published = _text(
                    record.get("published")
                    or record.get("published_at")
                    or record.get("date")
                    or record.get("datetime"),
                    "",
                )
                item = QListWidgetItem(f"[{kind}] {title}\n{source}  ·  {published}")
                url = record.get("url") or record.get("link")
                if url:
                    item.setData(Qt.ItemDataRole.UserRole, str(url))
            else:
                item = QListWidgetItem(f"[{kind}] {_text(record)}")
            self.list_widget.addItem(item)
        self.set_meta(f"{len(headlines)} HEADLINES · {len(events)} EVENTS")


class QuantPanel(Panel):
    def __init__(self, lqie_available: bool, trendline_status: str) -> None:
        super().__init__("LQIE Quant Lab", "ENGINE STATUS")
        self.add_note(f"LQIE package: {'AVAILABLE' if lqie_available else 'NOT FOUND'}", "goodText" if lqie_available else "warnText")
        self.add_note("Pattern engine: 0.5 experimental branch", "mutedText")
        self.add_note("Candlesticks: TA-Lib integration installed", "mutedText")
        self.add_note(f"Trendlines: {trendline_status}", "warnText" if "pending" in trendline_status.lower() else "mutedText")
        self.add_note("Analysis is not executed inside the desktop process. The LQIE engine remains a separate service/task.")


class DataLakePanel(Panel):
    def __init__(self) -> None:
        super().__init__("Data Lake", "LOCAL STORAGE")
        self.summary = self.add_note("Waiting for backend data-lake inventory…")
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["DATASET", "ROWS / FILES", "SIZE"])
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setShowGrid(False)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.content_layout.addWidget(self.table)
        self.refresh_local()

    def refresh_local(self) -> None:
        # Do not recursively walk a Windows-to-WSL UNC data lake on the GUI
        # thread. Use the backend's existing /api/overview inventory instead.
        if DATA_LAKE_ROOT.exists():
            self.summary.setText(f"DATA LAKE PATH ACCESSIBLE · {DATA_LAKE_ROOT}")
        else:
            self.summary.setText(f"DATA LAKE PATH NOT ACCESSIBLE · {DATA_LAKE_ROOT}")

    def update_overview(self, payload: dict[str, Any]) -> None:
        storage_bytes = payload.get("storage_bytes")
        company_count = payload.get("company_count")
        updated = payload.get("last_fundamentals_update")
        if storage_bytes is not None:
            try:
                storage_mb = float(storage_bytes) / (1024 * 1024)
                self.summary.setText(
                    f"{DATA_LAKE_ROOT}  ·  {storage_mb:.2f} MB TOTAL  ·  "
                    f"{company_count or 0} COMPANIES  ·  SEC UPDATE {updated or 'UNKNOWN'}"
                )
            except (TypeError, ValueError):
                pass

        datasets = payload.get("datasets")
        rows: list[list[str]] = []
        if isinstance(datasets, list):
            entries = [(None, item) for item in datasets]
        elif isinstance(datasets, dict):
            entries = list(datasets.items())
        else:
            entries = []

        for key, item in entries:
            if isinstance(item, dict):
                name = item.get("dataset") or item.get("name") or item.get("table") or item.get("path") or key
                count = item.get("rows", item.get("row_count", item.get("files", item.get("file_count", item.get("count", "—")))))
                size_bytes = item.get("size_bytes", item.get("bytes"))
                size = f"{float(size_bytes) / 1024:.1f} KB" if isinstance(size_bytes, (int, float)) else _text(item.get("size"), "—")
            else:
                name, count, size = key or "DATASET", "—", _text(item)
            rows.append([_text(name), _text(count), _text(size)])

        if rows:
            self.table.setRowCount(len(rows))
            for row_index, row in enumerate(rows):
                for col_index, value in enumerate(row):
                    self.table.setItem(row_index, col_index, QTableWidgetItem(value))
            self.table.resizeColumnsToContents()
        elif isinstance(datasets, dict) and "error" in datasets:
            self.summary.setText(f"DATA LAKE CATALOG ERROR · {datasets['error']}")


class SystemPanel(Panel):
    def __init__(self, api_url: str) -> None:
        super().__init__("System Status", "LOCAL NODE")
        self.backend = self.add_note("Backend: CHECKING…")
        self.backend_url = self.add_note(f"API endpoint: {api_url}")
        self.storage = self.add_note(f"Data lake: {DATA_LAKE_ROOT}")
        self.runtime = self.add_note("Desktop: Lionare Terminal 0.1.1")
        self.overview_label = self.add_note("API overview: waiting")
        self.health_label = self.add_note("Source monitor: waiting")
        self.last_update = self.add_note("Last refresh: —")

    def set_backend(self, online: bool, detail: str = "") -> None:
        self.backend.setText(f"Backend: {'ONLINE' if online else 'OFFLINE'}" + (f" · {detail}" if detail else ""))
        self.backend.setObjectName("goodText" if online else "warnText")
        self.backend.style().unpolish(self.backend)
        self.backend.style().polish(self.backend)
        self.last_update.setText("Last refresh: " + datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z"))

    def update_overview(self, payload: dict[str, Any]) -> None:
        version = _text(payload.get("version"), "unknown")
        count = _text(payload.get("company_count"), "—")
        self.overview_label.setText(f"API overview: backend {version} · {count} companies in universe")

    def update_health(self, payload: dict[str, Any]) -> None:
        if not payload:
            self.health_label.setText("Source monitor: no health snapshot returned")
            return
        sources = payload.get("sources") if isinstance(payload.get("sources"), dict) else payload
        if isinstance(sources, dict):
            self.health_label.setText(f"Source monitor: {len(sources)} source status entries")
        else:
            self.health_label.setText("Source monitor: health snapshot received")
        self.last_update.setText("Last refresh: " + datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z"))


class ChartWorkspace(QFrame):
    """Honest chart surface until a permitted, validated OHLCV source is wired in."""

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("chartWorkspace")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(8)
        top = QHBoxLayout()
        title = QLabel("MARKET WORKSPACE")
        title.setObjectName("chartTitle")
        top.addWidget(title)
        top.addStretch(1)
        self.symbol = QLabel("OHLCV · AWAITING MARKET DATA")
        self.symbol.setObjectName("panelMeta")
        top.addWidget(self.symbol)
        layout.addLayout(top)
        self.canvas = ChartCanvas()
        layout.addWidget(self.canvas, 1)
        footer = QLabel("MARKET PRICE FEED NOT CONNECTED · SEC FUNDAMENTALS ARE NOT STOCK PRICES")
        footer.setObjectName("warnText")
        layout.addWidget(footer)


class ChartCanvas(QWidget):
    def paintEvent(self, event: Any) -> None:  # noqa: N802 - Qt override
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect()
        painter.fillRect(rect, QColor("#090e15"))
        painter.setPen(QPen(QColor("#1c2a37"), 1, Qt.PenStyle.SolidLine))
        for i in range(1, 9):
            y = int(rect.height() * i / 9)
            painter.drawLine(0, y, rect.width(), y)
        for i in range(1, 13):
            x = int(rect.width() * i / 13)
            painter.drawLine(x, 0, x, rect.height())
        painter.setPen(QColor("#60758b"))
        painter.setFont(QFont("Consolas", 11))
        painter.drawText(
            rect,
            Qt.AlignmentFlag.AlignCenter,
            "WAITING FOR VALIDATED OHLCV DATA\n\nNo candles or prices are being fabricated.",
        )
        painter.end()
