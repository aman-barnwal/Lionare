from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QGridLayout,
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


def _format_metric(record: Any) -> str:
    if record is None:
        return "—"
    if isinstance(record, dict):
        value = record.get("usd_millions")
        year = record.get("year")
        if value is not None:
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
                pass
        return _text(record.get("value"))
    try:
        amount = float(record)
        return f"${amount:,.2f}"
    except (TypeError, ValueError):
        return _text(record)


class Panel(QWidget):
    """Content area for a dock; the QDockWidget title is the single panel heading."""

    def __init__(self, title: str, subtitle: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("panelBody")
        self.setMinimumHeight(105)
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
    def __init__(self, title: str, headers: list[str], rows: list[list[str]], subtitle: str = "") -> None:
        super().__init__(title, subtitle)
        self.table = QTableWidget(0, len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.table.setMinimumHeight(110)
        self.content_layout.addWidget(self.table)
        self.set_rows(rows)

    def set_rows(self, rows: list[list[str]]) -> None:
        self.table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            for c, value in enumerate(row):
                item = QTableWidgetItem(_text(value))
                item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
                self.table.setItem(r, c, item)
        self.table.resizeColumnsToContents()


class GlobalMarketsPanel(SimpleTablePanel):
    def __init__(self) -> None:
        rows = [[name, region, "—", "NO QUOTE FEED"] for name, region in GLOBAL_MARKETS]
        super().__init__("Global Markets", ["INDEX", "REGION", "LAST", "STATUS"], rows, "REFERENCE LIST · NO LIVE QUOTES")
        self.table.setColumnWidth(0, 125)
        self.table.setColumnWidth(1, 105)
        self.table.setColumnWidth(2, 65)


class WatchlistPanel(SimpleTablePanel):
    def __init__(self) -> None:
        rows = [[symbol, name, "—"] for symbol, name in WATCHLIST]
        super().__init__("Watchlist", ["SYMBOL", "COMPANY", "LAST"], rows, "INITIAL COMPANY UNIVERSE")
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
            else:
                symbol, company = _text(record), ""
            if symbol != "—":
                rows.append([symbol, company, "—"])
        if rows:
            self.set_rows(rows)
            self.set_meta(f"{len(rows)} COMPANIES · PRICE FEED NOT CONNECTED")


class CompanyResearchPanel(Panel):
    symbol_changed = Signal(str)

    def __init__(self) -> None:
        super().__init__("Company Research", "SEC FUNDAMENTALS · ANNUAL")
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
        self._selection_changed()

    def _selection_changed(self, *_: Any) -> None:
        symbol = str(self.selector.currentData() or "AAPL")
        self.company_meta.setText(f"{symbol} · REQUESTING COMPANY DATA")
        self.symbol_changed.emit(symbol)

    def update_company(self, payload: Any) -> None:
        record = payload
        if isinstance(payload, dict):
            for key in ("company", "data", "result"):
                if isinstance(payload.get(key), dict):
                    record = payload[key]
                    break
        if not isinstance(record, dict):
            self.company_meta.setText("Unexpected company response")
            return

        symbol = _text(record.get("symbol") or record.get("ticker"), str(self.selector.currentData() or "AAPL"))
        name = _text(record.get("name") or record.get("company_name"), symbol)
        sector = _text(record.get("sector") or record.get("industry"), "SEC XBRL")
        self.company_name.setText(name)
        self.company_meta.setText(f"{symbol}  ·  {sector}  ·  REPORTED FUNDAMENTALS, NOT MARKET PRICE")

        revenue = record.get("revenue_latest")
        income = record.get("net_income_latest")
        assets = record.get("assets_latest")
        metrics = record.get("metrics") if isinstance(record.get("metrics"), dict) else {}
        revenue_series = metrics.get("revenue") if isinstance(metrics.get("revenue"), list) else []
        self.metric_labels["revenue"].setText(_format_metric(revenue))
        self.metric_labels["net_income"].setText(_format_metric(income))
        self.metric_labels["assets"].setText(_format_metric(assets))
        years = record.get("revenue_years") or len(revenue_series)
        start = record.get("history_start")
        end = record.get("history_end")
        coverage = f"{years} FYs"
        if start and end:
            coverage += f"  ·  {start}–{end}"
        self.metric_labels["coverage"].setText(coverage)


class MarketPulsePanel(Panel):
    def __init__(self) -> None:
        super().__init__("Market Pulse", "AWAITING VERIFIED PRICE DATA")
        self.value = self.add_note("Market breadth and sentiment are not available yet.", "warnText")
        self.add_note("A permitted market-price feed is required before these statistics can be calculated.")


class PortfolioPanel(Panel):
    def __init__(self) -> None:
        super().__init__("Portfolio Summary", "NO PORTFOLIO")
        self.add_note("No portfolio has been configured.", "warnText")
        self.add_note("Holdings, exposure, daily P&L and returns will be calculated from saved positions and validated prices.")


class PerformancePanel(Panel):
    def __init__(self) -> None:
        super().__init__("Performance Tracker", "DATA SOURCE PENDING")
        self.add_note("No verified market-price history is connected.", "warnText")
        self.add_note("Performance metrics remain unavailable until a permitted OHLCV source is integrated.")


class NewsPanel(Panel):
    def __init__(self) -> None:
        super().__init__("News & Events", "OFFICIAL HEADLINES · GDELT EVENTS")
        self.list_widget = QListWidget()
        self.list_widget.setMinimumHeight(110)
        self.content_layout.addWidget(self.list_widget)
        self.list_widget.addItem("Waiting for the Lionare news service…")

    def update_news(self, payload: Any) -> None:
        self.list_widget.clear()
        if isinstance(payload, dict):
            headlines = payload.get("headlines") if isinstance(payload.get("headlines"), list) else []
            events = payload.get("events") if isinstance(payload.get("events"), list) else []
            records = [("HEADLINE", x) for x in headlines] + [("GDELT", x) for x in events]
        else:
            records = [("NEWS", x) for x in _extract_list(payload, ("news", "items", "articles", "results", "data"))]

        if not records:
            self.list_widget.addItem("No news records returned by the backend.")
            self.set_meta("NO CURRENT RECORDS")
            return

        # Keep the news panel readable; the full list remains in the data lake.
        for kind, record in records[:80]:
            if isinstance(record, dict):
                title = _text(record.get("title") or record.get("headline") or record.get("name"), "Untitled item")
                source = _text(record.get("source") or record.get("publisher") or record.get("domain"), kind)
                published = _text(record.get("published") or record.get("published_at") or record.get("date") or record.get("datetime"), "")
                item = QListWidgetItem(f"{title}\n{kind}  ·  {source}  ·  {published}")
                url = record.get("url") or record.get("link")
                if url:
                    item.setData(Qt.ItemDataRole.UserRole, str(url))
            else:
                item = QListWidgetItem(f"{_text(record)}\n{kind}")
            self.list_widget.addItem(item)
        self.set_meta(f"{len(headlines) if isinstance(payload, dict) else len(records)} HEADLINES  ·  {len(events) if isinstance(payload, dict) else 0} EVENTS")

    def set_error(self, message: str) -> None:
        self.list_widget.clear()
        self.list_widget.addItem(f"News service unavailable\n{message}")
        self.set_meta("REQUEST ERROR")


class QuantPanel(Panel):
    def __init__(self, lqie_available: bool, trendline_status: str) -> None:
        super().__init__("LQIE Quant Lab", "ENGINE STATUS")
        self.add_note(f"LQIE package: {'AVAILABLE' if lqie_available else 'NOT FOUND'}", "goodText" if lqie_available else "warnText")
        self.add_note("Pattern engine: 0.5 experimental branch")
        self.add_note("Candlesticks: TA-Lib integration installed")
        self.add_note(f"Trendlines: {trendline_status}", "warnText")
        self.add_note("Quantitative runs execute in the backend process, not in the desktop UI thread.")


class DataLakePanel(Panel):
    def __init__(self) -> None:
        super().__init__("Data Lake", "LOCAL STORAGE")
        self.summary = self.add_note(f"Data lake: {DATA_LAKE_ROOT}")
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["LAYER", "PARQUET FILES", "SIZE"])
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setShowGrid(False)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.content_layout.addWidget(self.table)
        self.add_note("Storage inventory is read-only from the desktop.")

    def update_overview(self, payload: Any) -> None:
        if not isinstance(payload, dict):
            return
        total = payload.get("storage_bytes")
        if total is not None:
            try:
                self.summary.setText(f"{DATA_LAKE_ROOT}  ·  {float(total) / (1024 * 1024):.2f} MB TOTAL")
            except (TypeError, ValueError):
                pass
        datasets = payload.get("datasets")
        # Dataset summary shape varies by DuckDB catalogue version; render only known list records.
        records = _extract_list(datasets, ("datasets", "items", "results"))
        if records:
            rows = []
            for record in records[:100]:
                if isinstance(record, dict):
                    rows.append([
                        _text(record.get("name") or record.get("dataset") or record.get("view")),
                        _text(record.get("rows") or record.get("row_count")),
                        _text(record.get("size") or record.get("size_bytes")),
                    ])
            if rows:
                self._set_rows(rows)

    def _set_rows(self, rows: list[list[str]]) -> None:
        self.table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            for column, value in enumerate(row):
                self.table.setItem(row_index, column, QTableWidgetItem(value))
        self.table.resizeColumnsToContents()

    def refresh_local(self) -> None:
        if not DATA_LAKE_ROOT.exists():
            self.summary.setText(f"Data lake path not accessible: {DATA_LAKE_ROOT}")
            self._set_rows([])
            return
        rows: list[list[str]] = []
        total_bytes = 0
        for layer in ("bronze", "silver", "gold", "catalog", "metadata"):
            path = DATA_LAKE_ROOT / layer
            files = list(path.rglob("*.parquet")) if path.exists() else []
            size = 0
            for file in files:
                try:
                    size += file.stat().st_size
                except OSError:
                    continue
            rows.append([layer.upper(), str(len(files)), f"{size / 1024:,.1f} KB"])
            total_bytes += size
        self.summary.setText(f"{DATA_LAKE_ROOT}  ·  {total_bytes / (1024 * 1024):.2f} MB PARQUET")
        self._set_rows(rows)


class SystemPanel(Panel):
    def __init__(self, api_url: str) -> None:
        super().__init__("System Status", "LOCAL NODE")
        self.backend = self.add_note("Backend: CHECKING…", "warnText")
        self.backend_url = self.add_note(f"API endpoint: {api_url}")
        self.storage = self.add_note(f"Data lake: {DATA_LAKE_ROOT}")
        self.runtime = self.add_note("Desktop: Lionare Terminal")
        self.last_update = self.add_note("Last refresh: —", "panelMeta")
        self.health = self.add_note("Source monitor: awaiting backend", "mutedText")

    def set_backend(self, online: bool, detail: str = "") -> None:
        self.backend.setText(f"Backend: {'ONLINE' if online else 'OFFLINE'}" + (f"  ·  {detail}" if detail else ""))
        self.backend.setObjectName("goodText" if online else "warnText")
        self.backend.style().unpolish(self.backend)
        self.backend.style().polish(self.backend)
        self.last_update.setText("Last refresh: " + datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z"))

    def update_health(self, payload: Any) -> None:
        if isinstance(payload, dict):
            sources = payload.get("sources")
            if isinstance(sources, dict):
                healthy = sum(1 for item in sources.values() if isinstance(item, dict) and item.get("status") in ("ok", "healthy", "online"))
                self.health.setText(f"Source monitor: {healthy}/{len(sources)} healthy")
            else:
                self.health.setText(f"Source monitor: {len(payload)} status fields")


class ChartWorkspace(QFrame):
    """Deliberately honest chart surface until validated OHLCV is connected."""

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("chartWorkspace")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 13, 16, 13)
        layout.setSpacing(9)

        top = QHBoxLayout()
        title_box = QVBoxLayout()
        title = QLabel("MARKET WORKSPACE")
        title.setObjectName("chartTitle")
        self.subtitle = QLabel("GLOBAL OVERVIEW  ·  REFERENCE DATA ONLY")
        self.subtitle.setObjectName("chartSubtitle")
        title_box.addWidget(title)
        title_box.addWidget(self.subtitle)
        top.addLayout(title_box)
        top.addStretch(1)
        self.instrument = QLabel("OHLCV  ·  AWAITING MARKET DATA")
        self.instrument.setObjectName("panelMeta")
        top.addWidget(self.instrument, 0, Qt.AlignmentFlag.AlignVCenter)
        layout.addLayout(top)

        self.canvas = ChartCanvas()
        layout.addWidget(self.canvas, 1)
        bottom = QHBoxLayout()
        note = QLabel("MARKET PRICE FEED NOT CONNECTED  ·  SEC FUNDAMENTALS ARE NOT STOCK PRICES")
        note.setObjectName("warnText")
        bottom.addWidget(note)
        bottom.addStretch(1)
        self.data_state = QLabel("NO VALIDATED OHLCV")
        self.data_state.setObjectName("panelMeta")
        bottom.addWidget(self.data_state)
        layout.addLayout(bottom)

    def set_workspace(self, name: str) -> None:
        subtitles = {
            "DASHBOARD": "GLOBAL OVERVIEW  ·  REFERENCE DATA ONLY",
            "MARKETS": "GLOBAL MARKETS  ·  PRICE FEED NOT CONNECTED",
            "EQUITY": "EQUITY RESEARCH  ·  SEC FUNDAMENTALS",
            "PORTFOLIO": "PORTFOLIO MONITOR  ·  NO SAVED POSITIONS",
            "NEWS": "NEWS & EVENTS  ·  INGESTED SOURCES",
            "QUANT LAB": "LQIE RESEARCH  ·  EXPERIMENTAL QUANTITATIVE ENGINE",
            "DATA LAKE": "LOCAL DATASETS  ·  BRONZE / SILVER / GOLD",
            "SYSTEM": "ENGINE HEALTH  ·  LOCAL SERVICES",
        }
        self.subtitle.setText(subtitles.get(name, name))


class ChartCanvas(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("chartCanvasFrame")
        self.setMinimumSize(400, 300)

    def paintEvent(self, event: Any) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect().adjusted(1, 1, -1, -1)
        painter.fillRect(rect, QColor("#080e15"))
        grid_pen = QPen(QColor("#1b2b3b"), 1)
        painter.setPen(grid_pen)
        for i in range(1, 8):
            y = int(rect.height() * i / 8)
            painter.drawLine(rect.left(), y, rect.right(), y)
        for i in range(1, 13):
            x = int(rect.width() * i / 13)
            painter.drawLine(x, rect.top(), x, rect.bottom())
        painter.setPen(QColor("#506a82"))
        painter.setFont(QFont("Consolas", 11))
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, "NO VALIDATED OHLCV DATA\n\nCandlesticks will appear when a permitted market-price source is connected.")
        painter.end()
