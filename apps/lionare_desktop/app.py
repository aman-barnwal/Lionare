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
        self.resize(1780, 1020)
        self.setMinimumSize(QSize(1360, 820))
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
        row = QHBoxLayout(header); row.setContentsMargins(12, 4, 12, 4); row.setSpacing(10)
        brand = QLabel("LIONARE"); brand.setObjectName("brandMark"); row.addWidget(brand)
        descriptor = QLabel("FINANCIAL INTELLIGENCE"); descriptor.setObjectName("brandDescriptor"); row.addWidget(descriptor)
        self.engine_badge = QLabel("●  CONNECTING"); self.engine_badge.setObjectName("badgeWarn"); row.addWidget(self.engine_badge)
        row.addStretch(1)
        self.clock_label = QLabel("--:--:--"); self.clock_label.setObjectName("clockLabel"); row.addWidget(self.clock_label)
        self.refresh_button = QPushButton("Refresh"); self.refresh_button.setObjectName("secondaryButton"); self.refresh_button.clicked.connect(self.refresh_all); row.addWidget(self.refresh_button)
        self._header_widget = header

        ticker = QWidget(); ticker.setObjectName("tickerStrip")
        ticker_row = QHBoxLayout(ticker); ticker_row.setContentsMargins(10, 3, 10, 3); ticker_row.setSpacing(5)
        tag = QLabel("REFERENCE WATCH"); tag.setObjectName("tickerCaption"); ticker_row.addWidget(tag)
        self.ticker_labels: list[QLabel] = []
        for symbol, _ in WATCHLIST[:8]:
            label = QLabel(f"{symbol}   SEC"); label.setObjectName("tickerPill"); ticker_row.addWidget(label); self.ticker_labels.append(label)
        ticker_row.addStretch(1)
        self.connection_text = QLabel("NO LIVE PRICE FEED"); self.connection_text.setObjectName("tickerStatus"); ticker_row.addWidget(self.connection_text)

        nav = QWidget(); nav.setObjectName("navStrip")
        nav_row = QHBoxLayout(nav); nav_row.setContentsMargins(9, 3, 9, 3); nav_row.setSpacing(3)
        self.nav_buttons: dict[str, QPushButton] = {}
        for name in WORKSPACES:
            button = QPushButton(name); button.setObjectName("navButton"); button.setCheckable(True)
            button.clicked.connect(lambda checked=False, item=name: self.activate_workspace(item))
            nav_row.addWidget(button); self.nav_buttons[name] = button
        nav_row.addStretch(1)
        self.workspace_tag = QLabel("DASHBOARD"); self.workspace_tag.setObjectName("workspaceTag"); nav_row.addWidget(self.workspace_tag)

        outer = QWidget(); outer_layout = QVBoxLayout(outer); outer_layout.setContentsMargins(0, 0, 0, 0); outer_layout.setSpacing(0)
        outer_layout.addWidget(header); outer_layout.addWidget(nav); outer_layout.addWidget(ticker)
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
        self.settings.clear(); self.resize(1780, 1020); self.activate_workspace("DASHBOARD")
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
        self.dashboard.set_backend(online, detail) if hasattr(self, "dashboard") else None
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
                self.dashboard.update_company(payload)
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
            self.dashboard.update_health(payload)
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
        QMainWindow, QWidget { background:#090b0e; color:#e5e9ed; font-family:'Segoe UI'; font-size:9pt; }
        QMenuBar { background:#080a0c; color:#c1c8cf; padding:2px 7px; border-bottom:1px solid #252b31; }
        QMenuBar::item { padding:5px 10px; } QMenuBar::item:selected { background:#171d23; }
        QMenu { background:#101419; border:1px solid #303840; } QMenu::item { padding:6px 20px; }
        QWidget#appHeader { background:#090b0e; border-bottom:1px solid #252c32; }
        QLabel#brandMark { color:#19d49a; font-size:17pt; font-weight:900; letter-spacing:2px; }
        QLabel#brandDescriptor { color:#8a969f; font-size:7pt; letter-spacing:2px; }
        QLabel#badgeGood { color:#19d99b; font-family:Consolas; font-size:8pt; font-weight:700; padding:4px 9px; background:#0c211a; border:1px solid #19533c; border-radius:2px; }
        QLabel#badgeWarn { color:#f1b34f; font-family:Consolas; font-size:8pt; font-weight:700; padding:4px 9px; background:#241b0e; border:1px solid #62491f; border-radius:2px; }
        QLabel#clockLabel { color:#f0b34f; font-family:Consolas; font-size:8pt; }
        QWidget#tickerStrip { background:#0d1115; border-top:1px solid #1e252b; border-bottom:1px solid #2b333b; }
        QLabel#tickerCaption { color:#e8a53b; font-family:Consolas; font-size:7pt; font-weight:700; }
        QLabel#tickerPill { color:#d3dbe2; background:#11171c; border:1px solid #303840; border-radius:1px; padding:4px 8px; font-family:Consolas; font-size:8pt; }
        QLabel#tickerStatus { color:#e5ab45; font-family:Consolas; font-size:7pt; }
        QWidget#navStrip { background:#0a0d10; border-bottom:1px solid #303840; }
        QPushButton#navButton { background:transparent; border:1px solid transparent; border-radius:1px; color:#b2bbc3; padding:7px 11px; font-size:8pt; font-weight:700; }
        QPushButton#navButton:hover { background:#171e24; border-color:#3b464f; color:#f0f3f6; }
        QPushButton#navButton:checked { background:#123526; color:#20d99d; border:1px solid #267452; }
        QLabel#workspaceTag { color:#20d99d; font-family:Consolas; font-size:7pt; padding:0 7px; }
        QPushButton { background:#131a20; color:#d3dbe2; border:1px solid #37414a; border-radius:1px; padding:5px 11px; }
        QPushButton:hover { background:#1b252d; border-color:#25805e; }
        QPushButton#secondaryButton { background:#11171c; color:#c4cdd5; }
        QWidget#pageRoot { background:#090b0e; }
        QLabel#terminalPageTitle { color:#f1f3f5; font-size:12pt; font-weight:800; letter-spacing:1px; }
        QLabel#terminalPageSubtitle { color:#929da6; font-family:Consolas; font-size:7pt; }
        QLabel#terminalPageStatus { color:#19d49a; font-family:Consolas; font-size:7pt; font-weight:700; }
        QFrame#terminalStat { background:#0d1216; border:0; border-bottom:1px solid #313940; }
        QLabel#terminalStatLabel { color:#8e9aa4; font-family:Consolas; font-size:7pt; font-weight:700; }
        QLabel#terminalStatValue { color:#e4e9ed; font-family:Consolas; font-size:9pt; font-weight:700; }
        QFrame#terminalStatDivider { background:#303941; }
        QFrame#surfaceCard { background:#0c1014; border:1px solid #303840; border-radius:1px; }
        QLabel#cardHeading { color:#edf1f4; font-size:9pt; font-weight:800; letter-spacing:.3px; }
        QLabel#cardMeta { color:#9aa5ae; font-family:Consolas; font-size:7pt; }
        QFrame#metricCard { background:#11171c; border:1px solid #303840; border-radius:1px; }
        QLabel#metricLabel { color:#98a3ac; font-family:Consolas; font-size:7pt; font-weight:700; }
        QLabel#metricValue { color:#f1f4f6; font-family:Consolas; font-size:13pt; font-weight:700; }
        QLabel#metricDetail { color:#9aa5ae; font-size:8pt; }
        QLabel#companyHero { color:#f2f5f7; font-size:15pt; font-weight:800; }
        QLabel#smallMuted { color:#9ba6af; font-size:8pt; }
        QLabel#warningText { color:#efb34f; font-size:8pt; }
        QLabel#focusCompany { color:#eef2f5; font-size:10pt; font-weight:800; padding:3px 1px; }
        QLabel#portfolioMetricLabel { color:#8f9ba5; font-family:Consolas; font-size:7pt; font-weight:700; }
        QLabel#portfolioMetricValue { color:#f0f3f5; font-family:Consolas; font-size:14pt; font-weight:700; }
        QWidget#pulseRow { background:#10161b; border-bottom:1px solid #263039; }
        QLabel#pulseLabel { color:#96a2ac; font-family:Consolas; font-size:7pt; font-weight:700; }
        QLabel#pulseGood { color:#1bd99b; font-family:Consolas; font-size:8pt; font-weight:700; }
        QLabel#pulseWarn { color:#f0b34f; font-family:Consolas; font-size:8pt; font-weight:700; }
        QLabel#pulseBad { color:#ff625c; font-family:Consolas; font-size:8pt; font-weight:700; }
        QLabel#pulseMuted { color:#b2bdc6; font-family:Consolas; font-size:8pt; }
        QLabel#pulseNote { color:#929da6; font-size:7pt; padding:4px 1px; }
        QComboBox { background:#0c1115; color:#e0e6eb; border:1px solid #39434c; border-radius:1px; padding:5px 9px; min-height:20px; font-size:8pt; }
        QComboBox QAbstractItemView { background:#11171c; color:#e0e7ed; selection-background-color:#174333; border:1px solid #303a43; }
        QTableWidget { background:#090d11; alternate-background-color:#0f1419; color:#dce3e8; border:1px solid #2a333b; border-radius:1px; gridline-color:transparent; selection-background-color:#17402f; selection-color:#fff; outline:0; font-family:Consolas; font-size:8pt; }
        QHeaderView::section { background:#141b21; color:#a4afb8; border:0; border-bottom:1px solid #38434c; padding:3px 7px; font-family:Consolas; font-size:7pt; font-weight:700; }
        QTableWidget::item { padding:1px 6px; border-bottom:1px solid #1f282f; }
        QListWidget { background:#090d11; color:#dce3e8; border:1px solid #2c353d; border-radius:1px; outline:0; font-size:8pt; }
        QListWidget::item { padding:8px 9px; border-bottom:1px solid #202930; }
        QListWidget::item:selected { background:#153b2c; }
        QTabWidget::pane { border:1px solid #2b353e; background:#0a0e12; border-radius:1px; }
        QTabBar::tab { background:#11171c; color:#a5b0b9; padding:7px 13px; border:1px solid #2c353d; font-size:8pt; }
        QTabBar::tab:selected { background:#143a2b; color:#20d99d; border-bottom:2px solid #19c98f; }
        QSplitter::handle { background:#252e35; width:4px; height:4px; }
        QSplitter::handle:hover { background:#16845f; }
        QStatusBar { background:#080a0c; color:#aab5be; border-top:1px solid #2b343c; font-family:Consolas; font-size:8pt; }
        QScrollBar:vertical { background:#090d10; width:9px; } QScrollBar::handle:vertical { background:#3b464f; min-height:24px; border-radius:1px; }
        QScrollBar:horizontal { background:#090d10; height:9px; } QScrollBar::handle:horizontal { background:#3b464f; min-width:24px; border-radius:1px; }
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
