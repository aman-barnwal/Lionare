from __future__ import annotations

import importlib.util
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlsplit

from PySide6.QtCore import Qt, QTimer, QSettings, QSize
from PySide6.QtGui import QAction, QFont
from PySide6.QtWidgets import (
    QApplication,
    QDockWidget,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from .config import API_BASE_URL, APP_NAME, APP_VERSION, REFRESH_INTERVAL_MS
from .services.backend_client import BackendClient
from .widgets.panels import (
    ChartWorkspace,
    CompanyResearchPanel,
    DataLakePanel,
    GlobalMarketsPanel,
    MarketPulsePanel,
    NewsPanel,
    PerformancePanel,
    PortfolioPanel,
    QuantPanel,
    SystemPanel,
    WatchlistPanel,
)


def _configure_logging() -> None:
    log_dir = Path.home() / "lionare-data" / "operations" / "desktop" / "logs"
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
        logging.basicConfig(
            filename=log_dir / "lionare_desktop.log",
            level=logging.INFO,
            format="%(asctime)s %(levelname)s %(message)s",
        )
    except OSError:
        logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


class LionareMainWindow(QMainWindow):
    """Native Lionare workstation. Heavy data and quant work stays in backend processes."""

    WORKSPACES = {
        "DASHBOARD": ("global", "company", "watchlist", "pulse", "news"),
        "MARKETS": ("global", "watchlist", "pulse", "performance"),
        "EQUITY": ("company", "watchlist", "news"),
        "PORTFOLIO": ("watchlist", "portfolio", "performance"),
        "NEWS": ("news",),
        "QUANT LAB": ("quant", "watchlist"),
        "DATA LAKE": ("data", "system"),
        "SYSTEM": ("system", "data"),
    }

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION}")
        self.resize(1640, 940)
        self.setMinimumSize(QSize(1240, 760))
        self.setDockNestingEnabled(True)
        self.setDockOptions(
            QMainWindow.DockOption.AllowNestedDocks
            | QMainWindow.DockOption.AllowTabbedDocks
            | QMainWindow.DockOption.AnimatedDocks
            | QMainWindow.DockOption.GroupedDragging
        )

        self.settings = QSettings("Lionex", "LionareTerminal_0_1_2")
        self.backend = BackendClient(API_BASE_URL, self)
        self.backend.received.connect(self._on_backend_data)
        self.backend.failed.connect(self._on_backend_error)
        self._backend_online = False
        self._latest_overview: Any = {}
        self._current_company_symbol = "AAPL"
        self._current_workspace = "DASHBOARD"

        self._build_menu()
        self._build_header()
        self._build_panels()
        self._build_status_bar()
        self._apply_theme()
        self._restore_window_state()

        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.refresh_all)
        self.refresh_timer.start(max(15_000, REFRESH_INTERVAL_MS))
        self.clock_timer = QTimer(self)
        self.clock_timer.timeout.connect(self._update_clock)
        self.clock_timer.start(1000)
        self._update_clock()
        self.refresh_all()
        logging.info("Lionare desktop %s started; API=%s", APP_VERSION, API_BASE_URL)

    # ---------- chrome ----------
    def _build_menu(self) -> None:
        file_menu = self.menuBar().addMenu("File")
        refresh_action = QAction("Refresh data", self)
        refresh_action.setShortcut("F5")
        refresh_action.triggered.connect(self.refresh_all)
        file_menu.addAction(refresh_action)
        save_action = QAction("Save workspace", self)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self.save_layout)
        file_menu.addAction(save_action)
        file_menu.addSeparator()
        exit_action = QAction("Exit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        self.view_menu = self.menuBar().addMenu("View")
        reset_action = QAction("Reset dashboard layout", self)
        reset_action.triggered.connect(self.reset_layout)
        self.view_menu.addAction(reset_action)
        self.view_menu.addSeparator()

        tools_menu = self.menuBar().addMenu("Tools")
        tools_menu.addAction(refresh_action)
        tools_menu.addAction(save_action)
        help_menu = self.menuBar().addMenu("Help")
        about_action = QAction("About Lionare", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    def _build_header(self) -> None:
        header = QToolBar("Lionare Header", self)
        header.setObjectName("headerToolbar")
        header.setMovable(False)
        header.setFloatable(False)
        header.setContentsMargins(4, 2, 4, 2)
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, header)

        brand = QLabel("LIONARE")
        brand.setObjectName("brandMark")
        header.addWidget(brand)
        descriptor = QLabel("  FINANCIAL INTELLIGENCE  ")
        descriptor.setObjectName("brandDescriptor")
        header.addWidget(descriptor)
        header.addSeparator()
        self.node_badge = QLabel("●  ENGINE CHECKING")
        self.node_badge.setObjectName("statusWarn")
        header.addWidget(self.node_badge)
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        header.addWidget(spacer)
        self.clock_label = QLabel("--:--:--")
        self.clock_label.setObjectName("clockLabel")
        header.addWidget(self.clock_label)

        ticker = QToolBar("Reference Watch", self)
        ticker.setObjectName("tickerToolbar")
        ticker.setMovable(False)
        ticker.setFloatable(False)
        self.addToolBarBreak(Qt.ToolBarArea.TopToolBarArea)
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, ticker)
        watch_label = QLabel("REFERENCE WATCH")
        watch_label.setObjectName("toolbarCaption")
        ticker.addWidget(watch_label)
        ticker.addSeparator()
        self.ticker_labels: list[QLabel] = []
        for symbol in ("AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "JPM", "XOM", "WMT", "COST"):
            label = QLabel(f"{symbol}   ·   SEC")
            label.setObjectName("tickerItem")
            ticker.addWidget(label)
            self.ticker_labels.append(label)
        ticker.addSeparator()
        refresh_btn = QPushButton("↻  REFRESH")
        refresh_btn.setObjectName("quietButton")
        refresh_btn.clicked.connect(self.refresh_all)
        ticker.addWidget(refresh_btn)

        nav = QToolBar("Workspaces", self)
        nav.setObjectName("navToolbar")
        nav.setMovable(False)
        nav.setFloatable(False)
        self.addToolBarBreak(Qt.ToolBarArea.TopToolBarArea)
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, nav)
        self.nav_buttons: dict[str, QPushButton] = {}
        for name in self.WORKSPACES:
            button = QPushButton(name)
            button.setObjectName("workspaceButton")
            button.setCheckable(True)
            button.setMinimumWidth(94)
            button.clicked.connect(lambda checked=False, workspace=name: self.activate_workspace(workspace))
            nav.addWidget(button)
            self.nav_buttons[name] = button
        self.nav_buttons["DASHBOARD"].setChecked(True)
        nav_spacer = QWidget()
        nav_spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        nav.addWidget(nav_spacer)
        self.workspace_label = QLabel("DASHBOARD")
        self.workspace_label.setObjectName("workspaceTag")
        nav.addWidget(self.workspace_label)

    # ---------- panels and dock layout ----------
    def _add_dock(self, key: str, title: str, widget: QWidget, area: Qt.DockWidgetArea) -> QDockWidget:
        dock = QDockWidget(title, self)
        dock.setObjectName(f"dock_{key}")
        dock.setWidget(widget)
        dock.setAllowedAreas(Qt.DockWidgetArea.AllDockWidgetAreas)
        dock.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetMovable
            | QDockWidget.DockWidgetFeature.DockWidgetFloatable
            | QDockWidget.DockWidgetFeature.DockWidgetClosable
        )
        dock.setMinimumWidth(250)
        dock.setMinimumHeight(125)
        self.addDockWidget(area, dock)
        self.docks[key] = dock
        self.view_menu.addAction(dock.toggleViewAction())
        return dock

    def _build_panels(self) -> None:
        self.docks: dict[str, QDockWidget] = {}
        self.chart_workspace = ChartWorkspace()
        self.setCentralWidget(self.chart_workspace)

        self.global_panel = GlobalMarketsPanel()
        self.company_panel = CompanyResearchPanel()
        self.company_panel.symbol_changed.connect(self._request_company)
        self.chart_workspace.metric_changed.connect(self._request_current_series)
        self.watchlist_panel = WatchlistPanel()
        self.pulse_panel = MarketPulsePanel()
        self.portfolio_panel = PortfolioPanel()
        self.performance_panel = PerformancePanel()
        self.news_panel = NewsPanel()

        project_root = Path(__file__).resolve().parents[2]
        src_path = project_root / "src"
        if src_path.exists() and str(src_path) not in sys.path:
            sys.path.insert(0, str(src_path))
        try:
            lqie_available = importlib.util.find_spec("lqie.patterns") is not None
        except (ImportError, ModuleNotFoundError, ValueError):
            lqie_available = False
        self.quant_panel = QuantPanel(lqie_available, "PATCH REQUIRED" if lqie_available else "PACKAGE NOT FOUND")
        self.data_panel = DataLakePanel()
        self.system_panel = SystemPanel(API_BASE_URL)

        self._add_dock("global", "GLOBAL MARKETS", self.global_panel, Qt.DockWidgetArea.LeftDockWidgetArea)
        self._add_dock("company", "COMPANY RESEARCH", self.company_panel, Qt.DockWidgetArea.LeftDockWidgetArea)
        self._add_dock("quant", "LQIE QUANT LAB", self.quant_panel, Qt.DockWidgetArea.LeftDockWidgetArea)
        self._add_dock("data", "DATA LAKE", self.data_panel, Qt.DockWidgetArea.LeftDockWidgetArea)
        self._add_dock("watchlist", "WATCHLIST", self.watchlist_panel, Qt.DockWidgetArea.RightDockWidgetArea)
        self._add_dock("pulse", "MARKET PULSE", self.pulse_panel, Qt.DockWidgetArea.RightDockWidgetArea)
        self._add_dock("system", "SYSTEM STATUS", self.system_panel, Qt.DockWidgetArea.RightDockWidgetArea)
        self._add_dock("news", "NEWS & EVENTS", self.news_panel, Qt.DockWidgetArea.BottomDockWidgetArea)
        self._add_dock("portfolio", "PORTFOLIO SUMMARY", self.portfolio_panel, Qt.DockWidgetArea.BottomDockWidgetArea)
        self._add_dock("performance", "PERFORMANCE TRACKER", self.performance_panel, Qt.DockWidgetArea.BottomDockWidgetArea)

        # Two purposeful side columns; secondary panels live in tabs instead of
        # shrinking every panel until its contents collide.
        self.splitDockWidget(self.docks["global"], self.docks["company"], Qt.Orientation.Vertical)
        self.tabifyDockWidget(self.docks["company"], self.docks["quant"])
        self.tabifyDockWidget(self.docks["company"], self.docks["data"])
        self.splitDockWidget(self.docks["watchlist"], self.docks["pulse"], Qt.Orientation.Vertical)
        self.tabifyDockWidget(self.docks["pulse"], self.docks["system"])
        self.tabifyDockWidget(self.docks["news"], self.docks["portfolio"])
        self.tabifyDockWidget(self.docks["news"], self.docks["performance"])
        self.resizeDocks(
            [self.docks["global"], self.docks["watchlist"]],
            [285, 315],
            Qt.Orientation.Horizontal,
        )
        self.resizeDocks(
            [self.docks["global"], self.docks["company"], self.docks["watchlist"], self.docks["pulse"]],
            [260, 300, 300, 250],
            Qt.Orientation.Vertical,
        )
        self.resizeDocks([self.docks["news"]], [190], Qt.Orientation.Vertical)
        self.activate_workspace("DASHBOARD")
        # The company selector emits during construction before the signal is connected.
        self._request_company(str(self.company_panel.selector.currentData() or "AAPL"))

    def _build_status_bar(self) -> None:
        self.status = self.statusBar()
        self.status.setObjectName("terminalStatusBar")
        self.status.showMessage("READY  ·  LOCAL WORKSTATION  ·  MARKET PRICE FEED NOT CONNECTED")

    # ---------- workspace switching ----------
    def activate_workspace(self, name: str) -> None:
        name = name.upper()
        if name not in self.WORKSPACES:
            return
        visible = set(self.WORKSPACES[name])
        for key, dock in self.docks.items():
            dock.setVisible(key in visible)
        # Raise the requested tab in each dock group after setting visibility.
        for key in self.WORKSPACES[name]:
            self.docks[key].raise_()
        for key, button in self.nav_buttons.items():
            button.setChecked(key == name)
        self._current_workspace = name
        self.workspace_label.setText(name)
        self.chart_workspace.set_workspace(name)
        if name == "DATA LAKE":
            # Refresh through the backend; do not scan the WSL-mounted lake on the GUI thread.
            self.backend.get("/api/overview")

    # ---------- persistence ----------
    def _restore_window_state(self) -> None:
        geometry = self.settings.value("geometry")
        state = self.settings.value("windowState")
        restored = False
        if geometry is not None and state is not None:
            restored = self.restoreGeometry(geometry) and self.restoreState(state)
        if not restored:
            self.resize(1640, 940)
            self.activate_workspace("DASHBOARD")

    def save_layout(self) -> None:
        self.settings.setValue("geometry", self.saveGeometry())
        self.settings.setValue("windowState", self.saveState())
        self.settings.setValue("workspace", self._current_workspace)
        self.settings.sync()
        self.status.showMessage("WORKSPACE LAYOUT SAVED", 3000)

    def reset_layout(self) -> None:
        self.settings.remove("geometry")
        self.settings.remove("windowState")
        self.settings.remove("workspace")
        self.resize(1640, 940)
        self.activate_workspace("DASHBOARD")
        self.status.showMessage("DEFAULT DASHBOARD LAYOUT RESTORED", 3000)

    # ---------- backend ----------
    def refresh_all(self) -> None:
        for endpoint in (
            "/api/health",
            "/api/overview",
            "/api/companies",
            "/api/news",
            "/api/lqie/status",
            "/api/lqie/runs?limit=30",
        ):
            self.backend.get(endpoint)
        self._request_company(self._current_company_symbol)

    def _request_company(self, symbol: str) -> None:
        symbol = symbol.upper().strip()
        if not symbol:
            return
        self._current_company_symbol = symbol
        self.backend.get(f"/api/company?symbol={quote(symbol)}")
        self._request_current_series()
        self._request_current_forecast()

    def _request_current_series(self, *_: Any) -> None:
        symbol = self._current_company_symbol
        metric = str(self.chart_workspace.metric_combo.currentData() or "revenue")
        self.backend.get(f"/api/series?symbol={quote(symbol)}&metric={quote(metric)}")

    def _request_current_forecast(self) -> None:
        symbol = self._current_company_symbol
        metric = str(self.chart_workspace.metric_combo.currentData() or "revenue")
        self.backend.get(f"/api/forecast?symbol={quote(symbol)}&metric={quote(metric)}")

    def _on_backend_data(self, path: str, payload: Any) -> None:
        route = urlsplit(path).path
        self._backend_online = True
        self.node_badge.setText("●  ENGINE ONLINE")
        self.node_badge.setObjectName("statusGood")
        self.node_badge.style().unpolish(self.node_badge)
        self.node_badge.style().polish(self.node_badge)
        self.system_panel.set_backend(True, "API responding")

        if route == "/api/overview":
            self._latest_overview = payload if isinstance(payload, dict) else {}
            version = self._latest_overview.get("version", "backend online") if isinstance(self._latest_overview, dict) else "backend online"
            self.system_panel.set_backend(True, f"API online · data service {version}")
            self.data_panel.update_overview(self._latest_overview)
        elif route == "/api/companies":
            self.watchlist_panel.update_companies(payload)
        elif route == "/api/company":
            if isinstance(payload, dict) and payload.get("symbol", self._current_company_symbol) == self._current_company_symbol:
                self.company_panel.update_company(payload)
        elif route == "/api/series":
            self.chart_workspace.set_series(payload, self._current_company_symbol, str(self.chart_workspace.metric_combo.currentData() or "revenue"))
        elif route == "/api/forecast":
            self.company_panel.update_forecast(payload)
        elif route == "/api/news":
            self.news_panel.update_news(payload)
        elif route == "/api/health":
            self.system_panel.update_health(payload)
        elif route == "/api/lqie/status":
            self.quant_panel.update_status(payload)
        elif route == "/api/lqie/runs":
            self.quant_panel.update_runs(payload)

        self.status.showMessage(f"ENGINE ONLINE  ·  {route.upper()} UPDATED", 2500)

    def _on_backend_error(self, path: str, message: str) -> None:
        route = urlsplit(path).path
        readable = message.strip() or "No error detail returned"
        if route == "/api/health" or route == "/api/overview":
            self._backend_online = False
            self.node_badge.setText("●  ENGINE OFFLINE")
            self.node_badge.setObjectName("statusWarn")
            self.node_badge.style().unpolish(self.node_badge)
            self.node_badge.style().polish(self.node_badge)
            self.system_panel.set_backend(False, f"{route}: {readable}")
        elif route == "/api/news":
            self.news_panel.set_error(readable)
        elif route in ("/api/company", "/api/forecast"):
            self.company_panel.set_error(readable)
        elif route == "/api/series":
            self.chart_workspace.set_error(readable)
        elif route.startswith("/api/lqie/"):
            self.quant_panel.summary.setText(f"LQIE API unavailable: {readable[:220]}")
        self.status.showMessage(f"API REQUEST ERROR  ·  {route}  ·  {readable}", 8000)
        logging.warning("Backend request failed %s: %s", path, readable)

    # ---------- polish ----------
    def _update_clock(self) -> None:
        now = datetime.now().astimezone()
        self.clock_label.setText(now.strftime("%d %b %y   %H:%M:%S %Z"))

    def _show_about(self) -> None:
        QMessageBox.about(
            self,
            "About Lionare",
            f"<b>{APP_NAME} {APP_VERSION}</b><br>Native financial intelligence workstation.<br><br>SEC fundamentals, news, data lake and LQIE run history are connected through the local backend. Market prices require a separate permitted OHLCV feed.",
        )

    def _apply_theme(self) -> None:
        self.setStyleSheet(r"""
            QMainWindow, QWidget {
                background: #0a1018; color: #d8e3ee;
                font-family: 'Segoe UI', 'Arial'; font-size: 9pt;
            }
            QMenuBar { background: #080d13; color: #aab9c9; border-bottom: 1px solid #1c2a38; padding: 3px 8px; }
            QMenuBar::item { padding: 5px 12px; background: transparent; }
            QMenuBar::item:selected { background: #172838; color: #fff; }
            QMenu { background: #101a25; border: 1px solid #26394a; }
            QMenu::item { padding: 7px 22px; }
            QMenu::item:selected { background: #1a3041; }
            QToolBar { background: #090f17; border: 0; spacing: 8px; padding: 5px 12px; }
            QToolBar#headerToolbar { border-bottom: 1px solid #1d2b39; }
            QToolBar#tickerToolbar { background: #0d1621; border-bottom: 1px solid #1d2b39; }
            QToolBar#navToolbar { background: #0b121b; border-bottom: 1px solid #263747; spacing: 6px; }
            QLabel#brandMark { color: #36d6b1; font-size: 20pt; font-weight: 900; letter-spacing: 2px; }
            QLabel#brandDescriptor { color: #748da6; font-size: 8pt; letter-spacing: 2px; }
            QLabel#toolbarCaption { color: #d29a45; font-family: Consolas, monospace; font-size: 8pt; font-weight: 700; }
            QLabel#tickerItem { color: #a8bfd2; font-family: Consolas, monospace; font-size: 8pt; padding: 3px 8px; }
            QLabel#clockLabel { color: #e0aa58; font-family: Consolas, monospace; font-size: 9pt; font-weight: 700; padding: 0 8px; }
            QLabel#statusWarn { color: #e5a34b; font-family: Consolas, monospace; font-size: 8pt; font-weight: 700; padding: 4px 8px; }
            QLabel#statusGood { color: #39d4a8; font-family: Consolas, monospace; font-size: 8pt; font-weight: 700; padding: 4px 8px; }
            QLabel#workspaceTag { color: #4bd5b2; font-family: Consolas, monospace; font-size: 8pt; padding: 5px 12px; }
            QPushButton { background: #111d29; color: #b8c9d9; border: 1px solid #26394b; border-radius: 4px; padding: 6px 11px; }
            QPushButton:hover { background: #1a2d3d; border-color: #3ac8a4; color: #fff; }
            QPushButton:checked { background: #15352f; color: #54e1b9; border: 1px solid #2aa889; }
            QPushButton#workspaceButton { min-height: 22px; padding: 5px 12px; font-size: 8pt; font-weight: 700; }
            QPushButton#quietButton { background: transparent; border-color: #304558; color: #8ca7bd; }
            QDockWidget { color: #dbe6ef; font-weight: 700; }
            QDockWidget::title { background: #111c28; padding: 9px 12px; border: 1px solid #26394b; border-bottom: 1px solid #30465a; letter-spacing: 1px; }
            QDockWidget::close-button, QDockWidget::float-button { background: transparent; border: 0; padding: 2px; }
            QTabBar::tab { background: #101a25; color: #8299ad; padding: 7px 14px; border: 1px solid #263747; }
            QTabBar::tab:selected { background: #172a39; color: #4ed9b4; border-bottom: 2px solid #36c6a3; }
            QWidget#panelBody { background: #0d1722; }
            QLabel#panelMeta { color: #708ba4; font-family: Consolas, monospace; font-size: 7pt; letter-spacing: .5px; }
            QLabel#mutedText { color: #8498aa; }
            QLabel#goodText { color: #42d7ad; }
            QLabel#warnText { color: #e1a14b; }
            QLabel#metricBlock { background: #132231; color: #e2ecf5; border: 1px solid #253b4d; border-radius: 4px; padding: 9px; font-family: Consolas, monospace; }
            QLabel#metricCaption { color: #7892aa; font-family: Consolas, monospace; font-size: 7pt; }
            QLabel#companyName { color: #eff5fa; font-size: 13pt; font-weight: 700; }
            QTableWidget, QListWidget { background: #0b141e; alternate-background-color: #101c28; color: #cbd8e5; border: 1px solid #1d3041; selection-background-color: #183a48; selection-color: #fff; outline: 0; }
            QHeaderView::section { background: #111e2b; color: #829bb2; border: 0; border-bottom: 1px solid #2a4053; padding: 7px 8px; font-size: 8pt; }
            QTableWidget::item { padding: 6px; border-bottom: 1px solid #172736; }
            QListWidget::item { padding: 9px 8px; border-bottom: 1px solid #1a2b3b; }
            QFrame#chartWorkspace { background: #0d1722; border: 1px solid #25394a; border-radius: 5px; }
            QLabel#chartTitle { color: #e9f1f8; font-weight: 800; letter-spacing: 2px; font-size: 11pt; }
            QLabel#chartSubtitle { color: #7792aa; font-family: Consolas, monospace; font-size: 8pt; }
            QFrame#chartCanvasFrame { background: #080e15; border: 1px solid #1c2c3c; border-radius: 3px; }
            QStatusBar { background: #080d13; color: #7f9aaf; border-top: 1px solid #263747; font-family: Consolas, monospace; font-size: 8pt; }
            QScrollBar:vertical { background: #0b1118; width: 10px; }
            QScrollBar::handle:vertical { background: #2a3e50; min-height: 26px; border-radius: 4px; }
            QScrollBar:horizontal { background: #0b1118; height: 10px; }
            QScrollBar::handle:horizontal { background: #2a3e50; min-width: 26px; border-radius: 4px; }
        """)

    def closeEvent(self, event: Any) -> None:
        self.save_layout()
        super().closeEvent(event)


def run() -> int:
    _configure_logging()
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName("Lionex")
    app.setFont(QFont("Segoe UI", 9))
    window = LionareMainWindow()
    window.show()
    return app.exec()
