from __future__ import annotations

import json
import math
from datetime import datetime
from typing import Any

from PySide6.QtCore import Qt, Signal, QRectF
from PySide6.QtGui import QColor, QDesktopServices, QFont, QPainter, QPainterPath, QPen, QBrush
from PySide6.QtWidgets import (
    QComboBox, QFrame, QGridLayout, QHBoxLayout, QLabel, QListWidget,
    QListWidgetItem, QSplitter, QTabWidget, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget, QHeaderView, QSizePolicy, QPushButton
)
from PySide6.QtCore import QUrl

from ..config import FUNDAMENTAL_METRICS, GLOBAL_MARKETS, WATCHLIST


COLORS = {
    "bg": "#0a1018", "surface": "#101b28", "surface2": "#132131",
    "border": "#243649", "grid": "#203143", "text": "#e3ecf4",
    "muted": "#8298ad", "teal": "#42d7b2", "cyan": "#61c4df",
    "amber": "#e5ad5a", "red": "#e47b78", "green": "#56d6a8",
}


def text(value: Any, fallback: str = "â€”") -> str:
    if value is None or value == "":
        return fallback
    if isinstance(value, (dict, list)):
        return json.dumps(value, default=str, ensure_ascii=False)[:160]
    return str(value)


def extract_list(payload: Any, *keys: str) -> list[Any]:
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in keys:
            val = payload.get(key)
            if isinstance(val, list):
                return val
    return []


def human_bytes(value: Any) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return text(value)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if number < 1024 or unit == "TB":
            return f"{number:,.1f} {unit}"
        number /= 1024
    return f"{number:,.1f} TB"


def amount_from_record(record: Any) -> float | None:
    if not isinstance(record, dict):
        try:
            return float(record)
        except (TypeError, ValueError):
            return None
    value = record.get("usd_millions")
    if value is not None:
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
    value = record.get("value")
    try:
        raw = float(value)
        return raw / 1_000_000 if record.get("unit") == "USD" else raw
    except (TypeError, ValueError):
        return None


def money_compact_millions(value: Any) -> str:
    try:
        value = float(value)
    except (TypeError, ValueError):
        return text(value)
    if abs(value) >= 1_000_000:
        return f"${value / 1_000_000:,.2f}T"
    if abs(value) >= 1_000:
        return f"${value / 1_000:,.2f}B"
    return f"${value:,.1f}M"


def money_record(record: Any) -> str:
    value = amount_from_record(record)
    if value is None:
        return "â€”"
    year = record.get("year") if isinstance(record, dict) else None
    out = money_compact_millions(value)
    return f"{out}  Â·  FY {year}" if year else out


def metric_label(metric: str) -> str:
    return dict(FUNDAMENTAL_METRICS).get(metric, metric.replace("_", " ").title())


class Card(QFrame):
    def __init__(self, title: str = "", subtitle: str = "", parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("surfaceCard")
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.box = QVBoxLayout(self)
        self.box.setContentsMargins(14, 12, 14, 13)
        self.box.setSpacing(9)
        if title:
            top = QHBoxLayout()
            self.heading = QLabel(title)
            self.heading.setObjectName("cardHeading")
            top.addWidget(self.heading)
            top.addStretch(1)
            self.meta = QLabel(subtitle)
            self.meta.setObjectName("cardMeta")
            top.addWidget(self.meta)
            self.box.addLayout(top)
        self.body = QVBoxLayout()
        self.body.setContentsMargins(0, 0, 0, 0)
        self.body.setSpacing(8)
        self.box.addLayout(self.body, 1)

    def set_meta(self, value: str) -> None:
        if hasattr(self, "meta"):
            self.meta.setText(value)


class MetricCard(QFrame):
    def __init__(self, label: str, value: str = "â€”", detail: str = ""):
        super().__init__()
        self.setObjectName("metricCard")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 11, 14, 12)
        layout.setSpacing(4)
        self.label = QLabel(label.upper())
        self.label.setObjectName("metricLabel")
        self.value = QLabel(value)
        self.value.setObjectName("metricValue")
        self.value.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.detail = QLabel(detail)
        self.detail.setObjectName("metricDetail")
        self.detail.setWordWrap(True)
        layout.addWidget(self.label)
        layout.addWidget(self.value)
        layout.addWidget(self.detail)

    def set_values(self, value: str, detail: str = "") -> None:
        self.value.setText(value)
        self.detail.setText(detail)


class SectionTitle(QWidget):
    def __init__(self, title: str, subtitle: str = ""):
        super().__init__()
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 4, 0, 6)
        row.setSpacing(12)
        self.title = QLabel(title)
        self.title.setObjectName("pageTitle")
        row.addWidget(self.title)
        if subtitle:
            sub = QLabel(subtitle)
            sub.setObjectName("pageSubtitle")
            row.addWidget(sub, 1, Qt.AlignmentFlag.AlignVCenter)


class DataTable(QTableWidget):
    def __init__(self, headers: list[str], parent: QWidget | None = None):
        super().__init__(0, len(headers), parent)
        self.setHorizontalHeaderLabels(headers)
        self.verticalHeader().setVisible(False)
        self.verticalHeader().setDefaultSectionSize(31)
        self.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.setAlternatingRowColors(True)
        self.setShowGrid(False)
        self.setWordWrap(False)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setSortingEnabled(False)
        self.horizontalHeader().setHighlightSections(False)
        self.horizontalHeader().setStretchLastSection(True)

    def fill(self, rows: list[list[Any]]) -> None:
        self.setUpdatesEnabled(False)
        self.setRowCount(len(rows))
        for r, values in enumerate(rows):
            for c, value in enumerate(values[: self.columnCount()]):
                item = QTableWidgetItem(text(value))
                item.setToolTip(text(value))
                item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
                self.setItem(r, c, item)
        self.setUpdatesEnabled(True)


class FundamentalChart(QWidget):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setMinimumHeight(260)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.records: list[dict[str, Any]] = []
        self.forecasts: list[dict[str, Any]] = []
        self.symbol = "AAPL"
        self.metric = "Revenue"
        self.state = "Choose a company to load reported annual fundamentals."

    def set_data(self, records: list[dict[str, Any]], symbol: str, metric: str, forecasts: list[dict[str, Any]] | None = None):
        self.records = records or []
        self.symbol = symbol
        self.metric = metric
        if forecasts is not None:
            self.forecasts = forecasts
        self.state = "" if len(self.records) >= 2 else "Not enough annual observations to draw a trend."
        self.update()

    def set_error(self, message: str):
        self.state = message[:180]
        self.update()

    def _series(self):
        out = []
        for row in self.records:
            try:
                year = int(row.get("year"))
                value = amount_from_record(row)
                if value is not None and math.isfinite(value):
                    out.append((year, value))
            except (TypeError, ValueError):
                continue
        return sorted(out)

    def _forecast_series(self):
        out = []
        for row in self.forecasts:
            if not isinstance(row, dict):
                continue
            year = row.get("year") or row.get("forecast_year")
            value = row.get("value_usd")
            if value is None:
                value = row.get("value", row.get("forecast"))
            if value is None and row.get("usd_millions") is not None:
                value = float(row["usd_millions"]) * 1_000_000
            try:
                year = int(year)
                amount = float(value)
                # Forecast APIs normally provide absolute USD; chart values use USD millions.
                if abs(amount) >= 10_000_000:
                    amount /= 1_000_000
                if math.isfinite(amount):
                    out.append((year, amount))
            except (TypeError, ValueError):
                continue
        return sorted(out)

    def _format_axis(self, value: float) -> str:
        return money_compact_millions(value)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), QColor("#0b1420"))
        data = self._series()
        forecast = self._forecast_series()
        if len(data) < 2:
            p.setPen(QColor(COLORS["muted"]))
            p.setFont(QFont("Segoe UI", 10))
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self.state or "Waiting for historical data")
            p.end()
            return

        all_points = data + forecast
        values = [v for _, v in all_points]
        lo, hi = min(values), max(values)
        if hi <= lo:
            hi = lo + max(abs(lo) * 0.05, 1.0)
        pad = (hi - lo) * 0.12
        lo -= pad
        hi += pad
        xmin, xmax = data[0][0], max(data[-1][0], forecast[-1][0] if forecast else data[-1][0])
        if xmax <= xmin:
            xmax = xmin + 1

        plot = self.rect().adjusted(84, 22, -28, -48)
        if plot.width() <= 10 or plot.height() <= 10:
            p.end(); return

        # Grid and y-axis labels.
        p.setFont(QFont("Consolas", 8))
        for i in range(5):
            frac = i / 4
            y = plot.top() + int(plot.height() * frac)
            value = hi - (hi - lo) * frac
            p.setPen(QPen(QColor(COLORS["grid"]), 1))
            p.drawLine(plot.left(), y, plot.right(), y)
            p.setPen(QColor(COLORS["muted"]))
            p.drawText(QRectF(3, y - 9, 75, 18), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, self._format_axis(value))
        for i in range(6):
            frac = i / 5
            x = plot.left() + int(plot.width() * frac)
            p.setPen(QPen(QColor(COLORS["grid"]), 1))
            p.drawLine(x, plot.top(), x, plot.bottom())

        def pt(year, value):
            x = plot.left() + (year - xmin) / (xmax - xmin) * plot.width()
            y = plot.bottom() - (value - lo) / (hi - lo) * plot.height()
            return x, y

        path = QPainterPath()
        first = pt(*data[0]); path.moveTo(*first)
        for point in data[1:]:
            path.lineTo(*pt(*point))
        fill = QPainterPath(path)
        fill.lineTo(*pt(data[-1][0], lo))
        fill.lineTo(*pt(data[0][0], lo))
        fill.closeSubpath()
        p.fillPath(fill, QColor(66, 215, 178, 24))
        p.setPen(QPen(QColor(COLORS["teal"]), 2.6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        p.drawPath(path)
        p.setBrush(QColor(COLORS["teal"]))
        p.setPen(Qt.PenStyle.NoPen)
        for year, value in data:
            x, y = pt(year, value)
            p.drawEllipse(QRectF(x - 3.3, y - 3.3, 6.6, 6.6))

        if forecast:
            forecast_points = [(data[-1][0], data[-1][1])] + forecast
            forecast_path = QPainterPath()
            forecast_path.moveTo(*pt(*forecast_points[0]))
            for point in forecast_points[1:]:
                forecast_path.lineTo(*pt(*point))
            p.setPen(QPen(QColor(COLORS["amber"]), 2.2, Qt.PenStyle.DashLine))
            p.drawPath(forecast_path)

        p.setPen(QColor(COLORS["muted"]))
        p.setFont(QFont("Consolas", 8))
        p.drawText(plot.left(), plot.bottom() + 28, str(xmin))
        p.drawText(plot.center().x() - 18, plot.bottom() + 28, str((xmin + xmax) // 2))
        p.drawText(plot.right() - 35, plot.bottom() + 28, str(xmax))
        p.setFont(QFont("Segoe UI", 9, QFont.Weight.DemiBold))
        p.setPen(QColor(COLORS["text"]))
        p.drawText(8, 15, f"{self.symbol}  Â·  {self.metric.upper()}  Â·  REPORTED SEC FUNDAMENTALS")
        p.setFont(QFont("Segoe UI", 8))
        p.setPen(QColor(COLORS["muted"]))
        p.drawText(self.width() - 155, 15, f"{len(data)} FY observations")
        p.end()


class ChartCard(Card):
    metric_changed = Signal(str)

    def __init__(self):
        super().__init__("Financial history", "SEC ANNUAL OBSERVATIONS")
        controls = QHBoxLayout()
        self.metric_combo = QComboBox()
        for key, label in FUNDAMENTAL_METRICS:
            self.metric_combo.addItem(label, key)
        self.metric_combo.setMinimumWidth(170)
        controls.addWidget(QLabel("Metric"))
        controls.addWidget(self.metric_combo)
        controls.addStretch(1)
        self.note = QLabel("Reported fundamentals Â· USD, annual")
        self.note.setObjectName("smallMuted")
        controls.addWidget(self.note)
        self.body.addLayout(controls)
        self.chart = FundamentalChart()
        self.body.addWidget(self.chart, 1)
        self.metric_combo.currentIndexChanged.connect(lambda: self.metric_changed.emit(str(self.metric_combo.currentData())))

    def set_series(self, payload: Any, symbol: str, metric: str, forecasts: list[dict[str, Any]] | None = None):
        series = payload.get("series", []) if isinstance(payload, dict) else []
        records = series[0].get("data", []) if series and isinstance(series[0], dict) else []
        label = payload.get("label", metric_label(metric)) if isinstance(payload, dict) else metric_label(metric)
        self.note.setText(f"{symbol} Â· {label} Â· USD")
        self.set_meta(f"{len(records)} ANNUAL OBSERVATIONS")
        self.chart.set_data(records, symbol, str(label), forecasts)


class GlobalMarketsCard(Card):
    def __init__(self):
        super().__init__("Global markets", "REFERENCE INDICES Â· NO QUOTES")
        self.table = DataTable(["Index", "Region", "Last"])
        self.table.fill([[name, region, "â€”"] for name, region in GLOBAL_MARKETS])
        self.table.setColumnWidth(0, 145)
        self.body.addWidget(self.table)
        self.note = QLabel("Live index quotes are not connected. Values are intentionally blank.")
        self.note.setObjectName("smallMuted")
        self.body.addWidget(self.note)


class WatchlistCard(Card):
    symbol_selected = Signal(str)

    def __init__(self):
        super().__init__("Company watchlist", "10-COMPANY UNIVERSE")
        self.table = DataTable(["Symbol", "Company", "Revenue"])
        self.table.setColumnWidth(0, 70)
        self.table.setColumnWidth(1, 145)
        self.table.setColumnWidth(2, 105)
        self.table.cellDoubleClicked.connect(self._activate_row)
        self.body.addWidget(self.table)
        self.note = QLabel("Double-click a company to open its equity research.")
        self.note.setObjectName("smallMuted")
        self.body.addWidget(self.note)
        self.update_companies([])

    def _activate_row(self, row: int, column: int):
        item = self.table.item(row, 0)
        if item:
            self.symbol_selected.emit(item.text())

    def update_companies(self, payload: Any):
        records = extract_list(payload, "companies", "items", "results", "data")
        if not records:
            records = [{"symbol": s, "name": n} for s, n in WATCHLIST]
        rows = []
        for item in records:
            if isinstance(item, dict):
                rows.append([text(item.get("symbol")), text(item.get("name")), money_record(item.get("revenue_latest"))])
        self.table.fill(rows)
        self.set_meta(f"{len(rows)} COMPANIES Â· REPORTED FUNDAMENTALS")


class CompanySummaryCard(Card):
    symbol_changed = Signal(str)

    def __init__(self):
        super().__init__("Company research", "SEC COMPANY FACTS")
        selector_row = QHBoxLayout()
        self.selector = QComboBox()
        for symbol, name in WATCHLIST:
            self.selector.addItem(f"{symbol}  â€”  {name}", symbol)
        self.selector.currentIndexChanged.connect(lambda: self.symbol_changed.emit(str(self.selector.currentData())))
        selector_row.addWidget(QLabel("Company"))
        selector_row.addWidget(self.selector, 1)
        self.body.addLayout(selector_row)
        self.name_label = QLabel("Select a company")
        self.name_label.setObjectName("companyHero")
        self.body.addWidget(self.name_label)
        self.meta_label = QLabel("Awaiting annual SEC facts")
        self.meta_label.setObjectName("smallMuted")
        self.body.addWidget(self.meta_label)
        grid = QGridLayout()
        grid.setHorizontalSpacing(10); grid.setVerticalSpacing(10)
        self.cards = {
            "revenue": MetricCard("Revenue"),
            "net_income": MetricCard("Net income"),
            "assets": MetricCard("Total assets"),
            "coverage": MetricCard("Historical coverage"),
        }
        for idx, card in enumerate(self.cards.values()):
            grid.addWidget(card, idx // 2, idx % 2)
        self.body.addLayout(grid)
        self.forecast = QLabel("Fundamental forecast will appear here.")
        self.forecast.setWordWrap(True)
        self.forecast.setObjectName("smallMuted")
        self.body.addWidget(self.forecast)
        self.warning = QLabel("Experimental fundamental trend only â€” not a share-price prediction or investment recommendation.")
        self.warning.setWordWrap(True)
        self.warning.setObjectName("warningText")
        self.body.addWidget(self.warning)
        self.body.addStretch(1)

    def set_company(self, payload: Any):
        if not isinstance(payload, dict):
            return
        symbol = text(payload.get("symbol"), "AAPL")
        name = text(payload.get("name"), symbol)
        sector = text(payload.get("sector"), "SEC XBRL")
        self.name_label.setText(name)
        self.meta_label.setText(f"{symbol}  Â·  {sector}  Â·  fiscal-year data")
        self.cards["revenue"].set_values(money_record(payload.get("revenue_latest")), f"FY {payload.get('history_end') or 'â€”'}")
        self.cards["net_income"].set_values(money_record(payload.get("net_income_latest")), "Latest reported fiscal year")
        self.cards["assets"].set_values(money_record(payload.get("assets_latest")), "Latest reported fiscal year")
        years = payload.get("revenue_years", 0)
        self.cards["coverage"].set_values(f"{years} fiscal years", f"{payload.get('history_start') or 'â€”'} â€“ {payload.get('history_end') or 'â€”'}")

    def set_forecast(self, payload: Any):
        if not isinstance(payload, dict):
            return
        forecasts = payload.get("forecasts", [])
        parts = []
        for row in forecasts:
            if not isinstance(row, dict):
                continue
            year = row.get("year") or row.get("forecast_year")
            value = row.get("value_usd", row.get("value", row.get("forecast")))
            if value is None and row.get("usd_millions") is not None:
                value = float(row["usd_millions"]) * 1_000_000
            try:
                parts.append(f"FY {year}: ${float(value)/1e9:,.1f}B")
            except (TypeError, ValueError):
                parts.append(f"FY {year}: {text(value)}")
        self.forecast.setText("Forecast  Â·  " + ("   |   ".join(parts) if parts else "No forecast returned"))
        self.warning.setText(text(payload.get("warning"), "Experimental historical trend; not a stock-price forecast."))

    def select_symbol(self, symbol: str):
        index = self.selector.findData(symbol)
        if index >= 0 and index != self.selector.currentIndex():
            self.selector.setCurrentIndex(index)


class NewsCard(Card):
    def __init__(self):
        super().__init__("News & events", "OFFICIAL FEEDS + GDELT")
        self.tabs = QTabWidget()
        self.headlines = QListWidget()
        self.events = QListWidget()
        self.tabs.addTab(self.headlines, "Official headlines")
        self.tabs.addTab(self.events, "GDELT events")
        self.body.addWidget(self.tabs)
        self.headlines.itemDoubleClicked.connect(self._open)
        self.events.itemDoubleClicked.connect(self._open)

    @staticmethod
    def _open(item: QListWidgetItem):
        url = item.data(Qt.ItemDataRole.UserRole)
        if url:
            QDesktopServices.openUrl(QUrl(str(url)))

    def _fill(self, widget: QListWidget, records: list[Any], label: str):
        widget.clear()
        if not records:
            widget.addItem(f"No {label.lower()} in the current backend response.")
            return
        for record in records[:200]:
            if isinstance(record, dict):
                title = text(record.get("title") or record.get("headline") or record.get("name"), "Untitled item")
                source = text(record.get("source") or record.get("publisher") or record.get("domain"), label)
                stamp = text(record.get("published") or record.get("published_at") or record.get("date") or record.get("datetime"), "")
                item = QListWidgetItem(f"{title}\n{source}   Â·   {stamp}")
                url = record.get("url") or record.get("link") or record.get("documentidentifier")
                if url and str(url).startswith(("http://", "https://")):
                    item.setData(Qt.ItemDataRole.UserRole, str(url))
            else:
                item = QListWidgetItem(text(record))
            widget.addItem(item)

    def update_news(self, payload: Any):
        headlines = payload.get("headlines", []) if isinstance(payload, dict) else []
        events = payload.get("events", []) if isinstance(payload, dict) else []
        headlines = headlines if isinstance(headlines, list) else []
        events = events if isinstance(events, list) else []
        self._fill(self.headlines, headlines, "official headlines")
        self._fill(self.events, events, "GDELT events")
        self.set_meta(f"{len(headlines)} HEADLINES  Â·  {len(events)} EVENTS")


class QuantCard(Card):
    def __init__(self):
        super().__init__("LQIE quantitative engine", "PATTERN ENGINE + RUN ARCHIVE")
        self.stats = QGridLayout()
        self.engine = MetricCard("Engine", "Checking", "")
        self.version = MetricCard("Version", "â€”", "")
        self.run_count = MetricCard("Archived runs", "â€”", "")
        self.gold_count = MetricCard("Gold outputs", "â€”", "")
        for i, card in enumerate((self.engine, self.version, self.run_count, self.gold_count)):
            self.stats.addWidget(card, 0, i)
        self.body.addLayout(self.stats)
        self.compat = QLabel("Trendline compatibility: awaiting diagnostic")
        self.compat.setObjectName("warningText")
        self.compat.setWordWrap(True)
        self.body.addWidget(self.compat)
        self.table = DataTable(["Run", "Symbol", "Timeframe", "Status", "Bars", "Detections"])
        self.body.addWidget(self.table, 1)
        self.note = QLabel("Run analyses in the LQIE worker/CLI. The desktop reads the archive; it does not run heavy calculations on the UI thread.")
        self.note.setObjectName("smallMuted")
        self.note.setWordWrap(True)
        self.body.addWidget(self.note)

    def update_status(self, payload: Any):
        if not isinstance(payload, dict):
            return
        available = bool(payload.get("engine_available"))
        self.engine.set_values("Available" if available else "Not found", "Python package")
        self.version.set_values(text(payload.get("engine_version")), "Pattern engine")
        self.run_count.set_values(str(payload.get("run_count", 0)), "Recorded in run index")
        self.gold_count.set_values(str(payload.get("gold_output_count", 0)), "Gold feature artifacts")
        diag = payload.get("trendline_compatibility") or {}
        self.compat.setText(f"Trendline diagnostic: {text(diag.get('status'))}  Â·  pandas {text(diag.get('pandas_version'))}  Â·  pytrendline {text(diag.get('pytrendline_version'))}")

    def update_runs(self, payload: Any):
        records = extract_list(payload, "runs", "items", "results")
        self.table.fill([[text(r.get("run_id")), text(r.get("symbol")), text(r.get("timeframe")), text(r.get("status")), text(r.get("bars_analysed")), text(r.get("pattern_detections"))] for r in records if isinstance(r, dict)])


class DataLakeCard(Card):
    def __init__(self):
        super().__init__("Data lake catalogue", "BRONZE Â· SILVER Â· GOLD Â· CATALOG")
        self.table = DataTable(["Dataset", "Rows", "Size", "Layer / source"])
        self.body.addWidget(self.table, 1)
        self.summary = QLabel("Waiting for backend dataset catalogueâ€¦")
        self.summary.setObjectName("smallMuted")
        self.body.addWidget(self.summary)

    def update_overview(self, payload: Any):
        if not isinstance(payload, dict):
            return
        data = payload.get("datasets", [])
        records = extract_list(data, "datasets", "items", "results")
        rows = []
        for record in records:
            if isinstance(record, dict):
                name = next((record.get(k) for k in ("name", "dataset", "view", "table", "dataset_name", "path") if record.get(k) not in (None, "")), "Unknown")
                count = next((record.get(k) for k in ("rows", "row_count", "records", "count", "num_rows") if record.get(k) is not None), "â€”")
                size = next((record.get(k) for k in ("size", "size_bytes", "bytes", "file_size") if record.get(k) is not None), None)
                detail = " Â· ".join(str(record[k]) for k in ("layer", "source", "format") if record.get(k) not in (None, ""))
                rows.append([name, f"{int(count):,}" if str(count).isdigit() else count, human_bytes(size) if size is not None else "â€”", detail])
            else:
                rows.append([text(record), "â€”", "â€”", ""])
        self.table.fill(rows)
        self.summary.setText(f"{len(records)} datasets  Â·  {human_bytes(payload.get('storage_bytes'))} total storage  Â·  {payload.get('company_count', 'â€”')} companies  Â·  Data service {text(payload.get('version'))}  Â·  Fundamentals updated {text(payload.get('last_fundamentals_update'))}")


class SystemCard(Card):
    def __init__(self, api_url: str):
        super().__init__("System & source health", "LOCAL BACKEND NODE")
        self.api_label = QLabel(f"API endpoint  Â·  {api_url}")
        self.api_label.setObjectName("smallMuted")
        self.body.addWidget(self.api_label)
        self.backend = MetricCard("Backend", "Checking", "Waiting for API response")
        self.probes = MetricCard("Source probes", "â€”", "Latest health snapshot")
        self.rss = MetricCard("RSS feeds", "â€”", "Latest health snapshot")
        self.gdelt = MetricCard("GDELT", "â€”", "Latest health snapshot")
        grid = QGridLayout()
        for i, card in enumerate((self.backend, self.probes, self.rss, self.gdelt)):
            grid.addWidget(card, 0, i)
        self.body.addLayout(grid)
        self.table = DataTable(["Type", "Source", "Status", "Details"])
        self.body.addWidget(self.table, 1)
        self.last = QLabel("Last health snapshot: â€”")
        self.last.setObjectName("smallMuted")
        self.body.addWidget(self.last)

    def set_backend(self, online: bool, detail: str = ""):
        self.backend.set_values("Online" if online else "Offline", detail)

    def update_health(self, payload: Any):
        if not isinstance(payload, dict):
            return
        probes = payload.get("probe_results", []) if isinstance(payload.get("probe_results"), list) else []
        rss = payload.get("rss_results", []) if isinstance(payload.get("rss_results"), list) else []
        gdelt = payload.get("gdelt_result", {}) if isinstance(payload.get("gdelt_result"), dict) else {}
        ok_states = {"ok", "healthy", "online", "success", "available", "200"}
        def count_ok(items):
            return sum(1 for x in items if isinstance(x, dict) and str(x.get("status", "")).lower() in ok_states)
        self.probes.set_values(f"{count_ok(probes)}/{len(probes)}", "Passed probes")
        self.rss.set_values(f"{count_ok(rss)}/{len(rss)}", "Available feeds")
        self.gdelt.set_values(text(gdelt.get("status")).title(), f"{gdelt.get('event_rows', 0)} event rows")
        rows = []
        for kind, items in (("Probe", probes), ("RSS", rss)):
            for item in items:
                if isinstance(item, dict):
                    rows.append([kind, text(item.get("source") or item.get("name") or item.get("url")), text(item.get("status")), text(item.get("detail") or item.get("message"))])
        if gdelt:
            rows.append(["GDELT", "GDELT export", text(gdelt.get("status")), f"{gdelt.get('event_rows', 0)} rows Â· {text(gdelt.get('latest_export_url'))}"])
        self.table.fill(rows)
        self.last.setText("Last health snapshot  Â·  " + text(payload.get("checked_at_utc")))


class DashboardPage(QWidget):
    company_selected = Signal(str)
    metric_changed = Signal(str)

    def __init__(self):
        super().__init__()
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 14, 18, 16)
        root.setSpacing(12)
        root.addWidget(SectionTitle("Dashboard", "Your financial intelligence overview"))
        kpis = QHBoxLayout(); kpis.setSpacing(10)
        self.kpi_companies = MetricCard("Companies", "10", "Tracked universe")
        self.kpi_datasets = MetricCard("Datasets", "â€”", "Data lake catalogue")
        self.kpi_storage = MetricCard("Data stored", "â€”", "Local lake footprint")
        self.kpi_news = MetricCard("News records", "â€”", "Official + GDELT")
        for card in (self.kpi_companies, self.kpi_datasets, self.kpi_storage, self.kpi_news):
            kpis.addWidget(card, 1)
        root.addLayout(kpis)
        middle = QSplitter(Qt.Orientation.Horizontal)
        middle.setChildrenCollapsible(False)
        self.global_card = GlobalMarketsCard()
        self.chart = ChartCard()
        self.watchlist = WatchlistCard()
        middle.addWidget(self.global_card)
        middle.addWidget(self.chart)
        middle.addWidget(self.watchlist)
        middle.setStretchFactor(0, 2); middle.setStretchFactor(1, 6); middle.setStretchFactor(2, 3)
        middle.setSizes([300, 850, 420])
        root.addWidget(middle, 5)
        self.news = NewsCard()
        self.news.setMaximumHeight(205)
        root.addWidget(self.news, 2)
        self.watchlist.symbol_selected.connect(self.company_selected.emit)
        self.chart.metric_changed.connect(self.metric_changed.emit)

    def update_overview(self, payload: Any):
        if not isinstance(payload, dict): return
        datasets = extract_list(payload.get("datasets"), "datasets", "items")
        self.kpi_companies.set_values(str(payload.get("company_count", "â€”")), "SEC company universe")
        self.kpi_datasets.set_values(str(len(datasets)), "Registered datasets")
        self.kpi_storage.set_values(human_bytes(payload.get("storage_bytes")), "Bronze through metadata")

    def update_news_count(self, headlines: int, events: int):
        self.kpi_news.set_values(f"{headlines + events:,}", f"{headlines} headlines Â· {events} events")


class EquityPage(QWidget):
    company_selected = Signal(str)
    metric_changed = Signal(str)

    def __init__(self):
        super().__init__()
        root = QVBoxLayout(self); root.setContentsMargins(18, 14, 18, 16); root.setSpacing(12)
        root.addWidget(SectionTitle("Equity research", "SEC-reported annual financials Â· not market prices"))
        self.company = CompanySummaryCard()
        root.addWidget(self.company)
        lower = QSplitter(Qt.Orientation.Horizontal); lower.setChildrenCollapsible(False)
        self.chart = ChartCard(); self.history = Card("Annual financial history", "REPORTED USD")
        self.history_table = DataTable(["Fiscal year", "Period end", "Value", "Filed", "Form"])
        self.history.body.addWidget(self.history_table)
        lower.addWidget(self.chart); lower.addWidget(self.history)
        lower.setStretchFactor(0, 6); lower.setStretchFactor(1, 4); lower.setSizes([900, 560])
        root.addWidget(lower, 1)
        self.company.symbol_changed.connect(self.company_selected.emit)
        self.chart.metric_changed.connect(self.metric_changed.emit)

    def set_company(self, payload: Any):
        self.company.set_company(payload)
        if isinstance(payload, dict):
            metrics = payload.get("metrics", {})
            metric = str(self.chart.metric_combo.currentData() or "revenue")
            records = metrics.get(metric, []) if isinstance(metrics, dict) else []
            self._fill_history(records)

    def set_forecast(self, payload: Any):
        self.company.set_forecast(payload)
        forecasts = payload.get("forecasts", []) if isinstance(payload, dict) else []
        self.chart.chart.forecasts = forecasts if isinstance(forecasts, list) else []
        self.chart.chart.update()

    def set_history(self, payload: Any, symbol: str, metric: str, forecasts: list[dict[str, Any]] | None = None):
        self.chart.set_series(payload, symbol, metric, forecasts)
        series = payload.get("series", []) if isinstance(payload, dict) else []
        records = series[0].get("data", []) if series and isinstance(series[0], dict) else []
        self._fill_history(records)

    def _fill_history(self, records: list[Any]):
        rows = []
        for r in reversed(records or []):
            if isinstance(r, dict):
                rows.append([text(r.get("year")), text(r.get("date")), money_record(r), text(r.get("filed")), text(r.get("form"))])
        self.history_table.fill(rows)

    def select_symbol(self, symbol: str):
        self.company.select_symbol(symbol)


class MarketsPage(QWidget):
    def __init__(self):
        super().__init__(); root = QVBoxLayout(self); root.setContentsMargins(18, 14, 18, 16); root.setSpacing(12)
        root.addWidget(SectionTitle("Markets", "Global reference universe Â· live quotes not yet connected"))
        row = QSplitter(Qt.Orientation.Horizontal); row.setChildrenCollapsible(False)
        self.global_card = GlobalMarketsCard(); self.watchlist = WatchlistCard()
        row.addWidget(self.global_card); row.addWidget(self.watchlist); row.setStretchFactor(0, 1); row.setStretchFactor(1, 2)
        root.addWidget(row, 3)
        self.notice = Card("Market data connection", "PRICE FEED REQUIRED")
        label = QLabel("The current data lake contains fundamentals, macro, rates, FX reference data and positioning datasets. It does not yet include a validated equity OHLCV price feed. Candlesticks, last prices and returns will appear here once a source with suitable access and display rights is connected.")
        label.setWordWrap(True); label.setObjectName("warningText"); self.notice.body.addWidget(label)
        root.addWidget(self.notice, 1)


class NewsPage(QWidget):
    def __init__(self):
        super().__init__(); root = QVBoxLayout(self); root.setContentsMargins(18, 14, 18, 16); root.setSpacing(12)
        root.addWidget(SectionTitle("News & events", "Official releases and GDELT event stream Â· double-click to open source"))
        self.card = NewsCard(); root.addWidget(self.card, 1)


class QuantPage(QWidget):
    def __init__(self):
        super().__init__(); root = QVBoxLayout(self); root.setContentsMargins(18, 14, 18, 16); root.setSpacing(12)
        root.addWidget(SectionTitle("Quant lab", "LQIE engine status, detector compatibility and experiment archive"))
        self.card = QuantCard(); root.addWidget(self.card, 1)


class DataLakePage(QWidget):
    def __init__(self):
        super().__init__(); root = QVBoxLayout(self); root.setContentsMargins(18, 14, 18, 16); root.setSpacing(12)
        root.addWidget(SectionTitle("Data lake", "Registered local datasets and storage inventory"))
        self.card = DataLakeCard(); root.addWidget(self.card, 1)


class SystemPage(QWidget):
    def __init__(self, api_url: str):
        super().__init__(); root = QVBoxLayout(self); root.setContentsMargins(18, 14, 18, 16); root.setSpacing(12)
        root.addWidget(SectionTitle("System health", "Backend connectivity and upstream source monitor"))
        self.card = SystemCard(api_url); root.addWidget(self.card, 1)


class PortfolioPage(QWidget):
    def __init__(self):
        super().__init__(); root = QVBoxLayout(self); root.setContentsMargins(18, 14, 18, 16); root.setSpacing(12)
        root.addWidget(SectionTitle("Portfolio", "Position tracking will be enabled after portfolio storage is implemented"))
        card = Card("Portfolio workspace", "NO PORTFOLIO CONFIGURED")
        label = QLabel("There are no saved positions yet. This workspace will support holdings, cash balances, cost basis, exposure, realised/unrealised P&L and performance once a portfolio ledger and validated price history are connected.")
        label.setWordWrap(True); label.setObjectName("smallMuted"); card.body.addWidget(label); root.addWidget(card, 1)

