from __future__ import annotations

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlsplit

from PySide6.QtCore import Qt, QTimer, QSettings, QSize, QSignalBlocker
from PySide6.QtGui import QAction, QFont
from PySide6.QtWidgets import (
    QApplication, QFrame, QHBoxLayout, QLabel, QMainWindow, QMessageBox,
    QPushButton, QSizePolicy, QStackedWidget, QToolBar, QVBoxLayout, QWidget,
)

from .config import API_BASE_URL, APP_NAME, APP_VERSION, REFRESH_INTERVAL_MS, WATCHLIST
from .services.backend_client import BackendClient
from .widgets.panels import (
    DashboardPage, EquityPage, MarketsPage, NewsPage, QuantPage,
    DataLakePage, SystemPage, PortfolioPage, text,
)


WORKSPACES = ("DASHBOARD", "MARKETS", "EQUITY", "PORTFOLIO", "NEWS", "QUANT LAB", "DATA LAKE", "SYSTEM")


def configure_logging() -> None:
    path = Path.home() / "lionare-data" / "operations" / "desktop" / "logs"
    try:
        path.mkdir(parents=True, exist_ok=True)
        logging.basicConfig(filename=path / "lionare_desktop.log", level=logging.INFO,
                            format="%(asctime)s %(levelname)s %(message)s")
    except OSError:
        logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


class LionareMainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION}")
        self.resize(1640, 980)
        self.setMinimumSize(QSize(1180, 760))
        self.settings = QSettings("Lionex", "LionareDesktop_0_1_4")
        self.backend = BackendClient(API_BASE_URL, self)
        self.backend.received.connect(self._on_backend_data)
        self.backend.failed.connect(self._on_backend_error)
        self.backend_online = False
        self.current_workspace = "DASHBOARD"
        self.current_symbol = "AAPL"
        self.current_metric = "revenue"
        self.overview: dict[str, Any] = {}
        self.company_payload: dict[str, Any] = {}
        self.forecast_payload: dict[str, Any] = {}
        self.series_payload: dict[str, Any] = {}
        self.news_payload: dict[str, Any] = {}

        self._build_menu()
        self._build_chrome()
        self._build_status()
        self._build_pages()
        self._theme()
        self._restore()

        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.refresh_all)
        self.refresh_timer.start(max(20_000, REFRESH_INTERVAL_MS))
        self.clock_timer = QTimer(self)
        self.clock_timer.timeout.connect(self._clock)
        self.clock_timer.start(1000)
        self._clock()
        self.refresh_all()
        logging.info("Lionare Desktop %s started at %s", APP_VERSION, API_BASE_URL)

    def _build_menu(self):
        file_menu = self.menuBar().addMenu("File")
        refresh = QAction("Refresh data", self); refresh.setShortcut("F5"); refresh.triggered.connect(self.refresh_all)
        save = QAction("Save workspace", self); save.setShortcut("Ctrl+S"); save.triggered.connect(self.save_workspace)
        exit_action = QAction("Exit", self); exit_action.setShortcut("Ctrl+Q"); exit_action.triggered.connect(self.close)
        file_menu.addAction(refresh); file_menu.addAction(save); file_menu.addSeparator(); file_menu.addAction(exit_action)
        view_menu = self.menuBar().addMenu("Workspace")
        for name in WORKSPACES:
            action = QAction(name.title(), self)
            action.triggered.connect(lambda checked=False, item=name: self.activate_workspace(item))
            view_menu.addAction(action)
        tools = self.menuBar().addMenu("Tools")
        tools.addAction(refresh); tools.addAction(save)
        reset = QAction("Reset layout", self); reset.triggered.connect(self.reset_workspace)
        tools.addAction(reset)
        help_menu = self.menuBar().addMenu("Help")
        about = QAction("About Lionare", self); about.triggered.connect(self._about); help_menu.addAction(about)

    def _build_chrome(self):
        header = QWidget(); header.setObjectName("appHeader")
        row = QHBoxLayout(header); row.setContentsMargins(18, 8, 18, 8); row.setSpacing(14)
        brand = QLabel("LIONARE"); brand.setObjectName("brandMark"); row.addWidget(brand)
        descriptor = QLabel("FINANCIAL INTELLIGENCE"); descriptor.setObjectName("brandDescriptor"); row.addWidget(descriptor)
        self.engine_badge = QLabel("●  CONNECTING"); self.engine_badge.setObjectName("badgeWarn"); row.addWidget(self.engine_badge)
        row.addStretch(1)
        self.clock_label = QLabel("--:--:--"); self.clock_label.setObjectName("clockLabel"); row.addWidget(self.clock_label)
        self.refresh_button = QPushButton("Refresh"); self.refresh_button.setObjectName("secondaryButton"); self.refresh_button.clicked.connect(self.refresh_all); row.addWidget(self.refresh_button)
        self._header_widget = header

        ticker = QWidget(); ticker.setObjectName("tickerStrip")
        ticker_row = QHBoxLayout(ticker); ticker_row.setContentsMargins(16, 5, 16, 5); ticker_row.setSpacing(8)
        tag = QLabel("REFERENCE WATCH"); tag.setObjectName("tickerCaption"); ticker_row.addWidget(tag)
        self.ticker_labels: list[QLabel] = []
        for symbol, _ in WATCHLIST[:8]:
            label = QLabel(f"{symbol}   SEC"); label.setObjectName("tickerPill"); ticker_row.addWidget(label); self.ticker_labels.append(label)
        ticker_row.addStretch(1)
        self.connection_text = QLabel("NO LIVE PRICE FEED"); self.connection_text.setObjectName("tickerStatus"); ticker_row.addWidget(self.connection_text)

        nav = QWidget(); nav.setObjectName("navStrip")
        nav_row = QHBoxLayout(nav); nav_row.setContentsMargins(14, 7, 14, 7); nav_row.setSpacing(7)
        self.nav_buttons: dict[str, QPushButton] = {}
        for name in WORKSPACES:
            button = QPushButton(name); button.setObjectName("navButton"); button.setCheckable(True)
            button.clicked.connect(lambda checked=False, item=name: self.activate_workspace(item))
            nav_row.addWidget(button); self.nav_buttons[name] = button
        nav_row.addStretch(1)
        self.workspace_tag = QLabel("DASHBOARD"); self.workspace_tag.setObjectName("workspaceTag"); nav_row.addWidget(self.workspace_tag)

        outer = QWidget(); outer_layout = QVBoxLayout(outer); outer_layout.setContentsMargins(0, 0, 0, 0); outer_layout.setSpacing(0)
        outer_layout.addWidget(header); outer_layout.addWidget(ticker); outer_layout.addWidget(nav)
        self._chrome_widget = outer

    def _build_pages(self):
        self.stack = QStackedWidget()
        self.pages: dict[str, QWidget] = {}
        self.dashboard = DashboardPage(); self.equity = EquityPage(); self.markets = MarketsPage()
        self.news = NewsPage(); self.quant = QuantPage(); self.data = DataLakePage()
        self.system = SystemPage(API_BASE_URL); self.portfolio = PortfolioPage()
        for key, page in (
            ("DASHBOARD", self.dashboard), ("MARKETS", self.markets), ("EQUITY", self.equity),
            ("PORTFOLIO", self.portfolio), ("NEWS", self.news), ("QUANT LAB", self.quant),
            ("DATA LAKE", self.data), ("SYSTEM", self.system),
        ):
            self.pages[key] = page
            self.stack.addWidget(page)

        self.dashboard.company_selected.connect(self._select_company)
        self.dashboard.metric_changed.connect(self._select_metric)
        self.equity.company_selected.connect(self._select_company)
        self.equity.metric_changed.connect(self._select_metric)
        self.markets.watchlist.symbol_selected.connect(self._select_company)
        self.setCentralWidget(self._compose_central())
        self.activate_workspace("DASHBOARD")

    def _compose_central(self) -> QWidget:
        wrapper = QWidget(); layout = QVBoxLayout(wrapper)
        layout.setContentsMargins(0, 0, 0, 0); layout.setSpacing(0)
        layout.addWidget(self._chrome_widget)
        layout.addWidget(self.stack, 1)
        return wrapper

    def _build_status(self):
        self.status = self.statusBar()
        self.status.setObjectName("terminalStatusBar")
        self.status.showMessage("READY  ·  SEC FUNDAMENTALS CONNECTED THROUGH LOCAL BACKEND  ·  MARKET PRICE FEED NOT CONNECTED")

    def activate_workspace(self, name: str):
        if name not in self.pages: return
        self.current_workspace = name
        self.stack.setCurrentWidget(self.pages[name])
        for key, button in self.nav_buttons.items():
            button.setChecked(key == name)
        self.workspace_tag.setText(name)
        self.status.showMessage(f"{name} WORKSPACE", 1800)
        if name == "EQUITY":
            self._request_company(self.current_symbol)

    def _restore(self):
        geometry = self.settings.value("geometry")
        if geometry is not None:
            self.restoreGeometry(geometry)
        workspace = str(self.settings.value("workspace", "DASHBOARD"))
        self.activate_workspace(workspace if workspace in self.pages else "DASHBOARD")

    def save_workspace(self):
        self.settings.setValue("geometry", self.saveGeometry())
        self.settings.setValue("workspace", self.current_workspace)
        self.settings.sync()
        self.status.showMessage("WORKSPACE SAVED", 2500)

    def reset_workspace(self):
        self.settings.clear(); self.resize(1640, 980); self.activate_workspace("DASHBOARD")
        self.status.showMessage("DEFAULT WORKSPACE RESTORED", 2500)

    def refresh_all(self):
        for endpoint in ("/api/health", "/api/overview", "/api/companies", "/api/news", "/api/lqie/status", "/api/lqie/runs?limit=50"):
            self.backend.get(endpoint)
        self._request_company(self.current_symbol)
        self.status.showMessage("REFRESH REQUESTS SENT TO LIONARE ENGINE", 1800)

    def _select_company(self, symbol: str):
        symbol = str(symbol or "").upper().strip()
        if not symbol or symbol == self.current_symbol:
            return
        self.current_symbol = symbol
        self._sync_company_selectors(symbol)
        self._request_company(symbol)

    def _sync_company_selectors(self, symbol: str):
        for combo in (self.equity.company.selector,):
            blocker = QSignalBlocker(combo)
            index = combo.findData(symbol)
            if index >= 0: combo.setCurrentIndex(index)
            del blocker

    def _select_metric(self, metric: str):
        metric = str(metric or "revenue")
        if metric == self.current_metric:
            return
        self.current_metric = metric
        self._sync_metric_selectors(metric)
        self._request_series()
        self._request_forecast()

    def _sync_metric_selectors(self, metric: str):
        combos = (self.dashboard.chart.metric_combo, self.equity.chart.metric_combo)
        for combo in combos:
            blocker = QSignalBlocker(combo)
            idx = combo.findData(metric)
            if idx >= 0: combo.setCurrentIndex(idx)
            del blocker

    def _request_company(self, symbol: str):
        self.current_symbol = symbol.upper()
        self.forecast_payload = {}
        self.series_payload = {}
        # Clear the previous company trace while the selected company's data loads.
        self.dashboard.chart.chart.set_data([], self.current_symbol, self.current_metric, [])
        self.equity.chart.chart.set_data([], self.current_symbol, self.current_metric, [])
        self.backend.get(f"/api/company?symbol={quote(self.current_symbol)}")
        self._request_series(); self._request_forecast()

    def _request_series(self):
        self.backend.get(f"/api/series?symbol={quote(self.current_symbol)}&metric={quote(self.current_metric)}")

    def _request_forecast(self):
        self.backend.get(f"/api/forecast?symbol={quote(self.current_symbol)}&metric={quote(self.current_metric)}")

    def _set_online(self, online: bool, detail: str = ""):
        self.backend_online = online
        self.engine_badge.setText("●  ENGINE ONLINE" if online else "●  ENGINE OFFLINE")
        self.engine_badge.setObjectName("badgeGood" if online else "badgeWarn")
        self.engine_badge.style().unpolish(self.engine_badge); self.engine_badge.style().polish(self.engine_badge)
        self.system.card.set_backend(online, detail)
        if online:
            self.connection_text.setText("FUNDAMENTALS ONLINE · QUOTES NOT CONNECTED")

    def _on_backend_data(self, path: str, payload: Any):
        route = urlsplit(path).path
        self._set_online(True, "API responding")
        if route == "/api/overview":
            self.overview = payload if isinstance(payload, dict) else {}
            self.dashboard.update_overview(self.overview)
            self.data.card.update_overview(self.overview)
        elif route == "/api/companies":
            self.dashboard.watchlist.update_companies(payload)
            self.markets.watchlist.update_companies(payload)
        elif route == "/api/company":
            if isinstance(payload, dict) and payload.get("symbol") == self.current_symbol:
                self.company_payload = payload
                self.equity.set_company(payload)
        elif route == "/api/series":
            incoming = payload if isinstance(payload, dict) else {}
            series = incoming.get("series", [])
            response_symbol = series[0].get("symbol") if series and isinstance(series[0], dict) else None
            if response_symbol and response_symbol != self.current_symbol:
                return
            self.series_payload = incoming
            self.dashboard.chart.set_series(self.series_payload, self.current_symbol, self.current_metric,
                                            self.forecast_payload.get("forecasts", []))
            self.equity.set_history(self.series_payload, self.current_symbol, self.current_metric,
                                    self.forecast_payload.get("forecasts", []))
        elif route == "/api/forecast":
            if isinstance(payload, dict) and payload.get("symbol") and payload.get("symbol") != self.current_symbol:
                return
            self.forecast_payload = payload if isinstance(payload, dict) else {}
            self.equity.set_forecast(self.forecast_payload)
            if self.series_payload:
                self.dashboard.chart.set_series(self.series_payload, self.current_symbol, self.current_metric,
                                                self.forecast_payload.get("forecasts", []))
                self.equity.set_history(self.series_payload, self.current_symbol, self.current_metric,
                                        self.forecast_payload.get("forecasts", []))
        elif route == "/api/news":
            self.news_payload = payload if isinstance(payload, dict) else {}
            self.dashboard.news.update_news(self.news_payload)
            self.news.card.update_news(self.news_payload)
            self.dashboard.update_news_count(len(self.news_payload.get("headlines", [])), len(self.news_payload.get("events", [])))
        elif route == "/api/health":
            self.system.card.update_health(payload)
        elif route == "/api/lqie/status":
            self.quant.card.update_status(payload)
        elif route == "/api/lqie/runs":
            self.quant.card.update_runs(payload)
        self.status.showMessage(f"ENGINE ONLINE  ·  {route.upper()} UPDATED", 2200)

    def _on_backend_error(self, path: str, message: str):
        route = urlsplit(path).path
        detail = message.strip() or "No error detail returned"
        if route in ("/api/overview", "/api/health"):
            self._set_online(False, detail)
        elif route in ("/api/series", "/api/forecast"):
            self.dashboard.chart.chart.set_error(detail)
            self.equity.chart.chart.set_error(detail)
        elif route.startswith("/api/lqie/"):
            self.quant.card.compat.setText("LQIE API unavailable  ·  " + detail[:240])
        elif route == "/api/news":
            self.news.card.set_meta("REQUEST ERROR")
        self.status.showMessage(f"API ERROR  ·  {route}  ·  {detail[:180]}", 6000)
        logging.warning("Backend request failed %s: %s", path, detail)

    def _clock(self):
        self.clock_label.setText(datetime.now().astimezone().strftime("%d %b %Y   %H:%M:%S %Z"))

    def _about(self):
        QMessageBox.about(self, "About Lionare", f"<b>{APP_NAME} {APP_VERSION}</b><br>Native financial intelligence workstation.<br><br>Company financials, news, data lake inventory and LQIE run history are served by the local Lionare backend. Equity quote and OHLCV market feeds are not yet connected.")

    def _theme(self):
        self.setStyleSheet(r"""
        QMainWindow, QWidget { background:#0a1018; color:#dce6ef; font-family:'Segoe UI'; font-size:9pt; }
        QMenuBar { background:#080d13; color:#b9c7d5; padding:5px 8px; border-bottom:1px solid #1d2b39; }
        QMenuBar::item { padding:6px 12px; } QMenuBar::item:selected { background:#182938; }
        QMenu { background:#111c28; border:1px solid #2b4053; } QMenu::item { padding:7px 22px; }
        QWidget#appHeader { background:#0b121b; border-bottom:1px solid #213244; }
        QLabel#brandMark { color:#42d7b2; font-size:22pt; font-weight:900; letter-spacing:2px; }
        QLabel#brandDescriptor { color:#7f95a9; font-size:8pt; letter-spacing:2px; }
        QLabel#badgeGood { color:#4bddb6; font-family:Consolas; font-weight:700; padding:5px 10px; background:#102a27; border:1px solid #1f5147; border-radius:4px; }
        QLabel#badgeWarn { color:#e6ad5a; font-family:Consolas; font-weight:700; padding:5px 10px; background:#2b2115; border:1px solid #5b4526; border-radius:4px; }
        QLabel#clockLabel { color:#dfb16b; font-family:Consolas; font-size:9pt; }
        QWidget#tickerStrip { background:#0e1722; border-bottom:1px solid #1c2c3d; }
        QLabel#tickerCaption { color:#d2a35b; font-family:Consolas; font-size:8pt; font-weight:700; }
        QLabel#tickerPill { color:#a8bfd2; background:#121f2d; border:1px solid #223649; border-radius:3px; padding:6px 9px; font-family:Consolas; font-size:8pt; }
        QLabel#tickerStatus { color:#d4a65f; font-family:Consolas; font-size:8pt; }
        QWidget#navStrip { background:#0b121a; border-bottom:1px solid #27394b; }
        QPushButton#navButton { background:transparent; border:1px solid transparent; border-radius:4px; color:#9fb1c2; padding:9px 13px; font-size:8pt; font-weight:700; }
        QPushButton#navButton:hover { background:#142232; border-color:#2a4054; color:#edf4fa; }
        QPushButton#navButton:checked { background:#14352f; color:#57dfbb; border:1px solid #2d9e83; }
        QLabel#workspaceTag { color:#4bd8b5; font-family:Consolas; font-size:8pt; padding:0 9px; }
        QPushButton { background:#142130; color:#c2d0dc; border:1px solid #2a4053; border-radius:4px; padding:7px 12px; }
        QPushButton:hover { background:#1b3042; border-color:#3c9e89; }
        QPushButton#secondaryButton { background:#111e2b; color:#afc2d3; }
        QWidget#pageRoot { background:#0a1018; }
        QLabel#pageTitle { color:#edf3f8; font-size:17pt; font-weight:700; }
        QLabel#pageSubtitle { color:#8399ad; font-size:9pt; }
        QFrame#surfaceCard { background:#101b28; border:1px solid #263a4d; border-radius:7px; }
        QLabel#cardHeading { color:#dce7f0; font-size:10pt; font-weight:700; }
        QLabel#cardMeta { color:#7992a8; font-family:Consolas; font-size:7pt; }
        QFrame#metricCard { background:#132232; border:1px solid #294055; border-radius:6px; }
        QLabel#metricLabel { color:#829ab0; font-family:Consolas; font-size:7pt; font-weight:700; }
        QLabel#metricValue { color:#edf5fa; font-size:15pt; font-weight:700; }
        QLabel#metricDetail { color:#8299ae; font-size:8pt; }
        QLabel#companyHero { color:#f0f5f9; font-size:16pt; font-weight:700; }
        QLabel#smallMuted { color:#8499ac; font-size:8pt; }
        QLabel#warningText { color:#e2ad61; font-size:8pt; }
        QComboBox { background:#0c1722; color:#dce8f0; border:1px solid #2a4054; border-radius:4px; padding:7px 10px; min-height:22px; }
        QComboBox QAbstractItemView { background:#111d29; color:#e0e9f1; selection-background-color:#1a3b43; border:1px solid #2b4155; }
        QTableWidget { background:#0c1621; alternate-background-color:#101d2a; color:#d1deea; border:1px solid #24394c; border-radius:4px; gridline-color:transparent; selection-background-color:#19404a; selection-color:#fff; outline:0; }
        QHeaderView::section { background:#142333; color:#91a7ba; border:0; border-bottom:1px solid #2b4054; padding:8px 9px; font-size:8pt; font-weight:700; }
        QTableWidget::item { padding:6px 8px; border-bottom:1px solid #1b2b3b; }
        QListWidget { background:#0c1621; color:#d1deea; border:1px solid #24394c; border-radius:4px; outline:0; }
        QListWidget::item { padding:10px 11px; border-bottom:1px solid #1d2d3c; }
        QListWidget::item:selected { background:#163443; }
        QTabWidget::pane { border:1px solid #26394b; background:#0c1621; border-radius:4px; }
        QTabBar::tab { background:#111d29; color:#90a6b9; padding:9px 16px; border:1px solid #26394b; }
        QTabBar::tab:selected { background:#17332f; color:#50dcb6; border-bottom:2px solid #42c9a6; }
        QSplitter::handle { background:#0a1018; width:5px; height:5px; }
        QStatusBar { background:#080d13; color:#8da5b8; border-top:1px solid #243749; font-family:Consolas; font-size:8pt; }
        QScrollBar:vertical { background:#0b131c; width:10px; } QScrollBar::handle:vertical { background:#2b4053; min-height:24px; border-radius:4px; }
        QScrollBar:horizontal { background:#0b131c; height:9px; } QScrollBar::handle:horizontal { background:#2b4053; min-width:22px; border-radius:4px; }
        """)

    def closeEvent(self, event):
        self.save_workspace()
        super().closeEvent(event)


def run() -> int:
    configure_logging()
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName("Lionex")
    app.setFont(QFont("Segoe UI", 9))
    window = LionareMainWindow()
    window.show()
    return app.exec()
