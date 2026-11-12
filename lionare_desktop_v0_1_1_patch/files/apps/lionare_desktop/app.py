from __future__ import annotations

import importlib.util
import logging
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import quote
from typing import Any

from PySide6.QtCore import Qt, QTimer, QSettings, QSize
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QDockWidget,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QToolBar,
    QWidget,
)

from .config import (
    API_BASE_URL,
    APP_NAME,
    APP_VERSION,
    DATA_LAKE_ROOT,
    REFRESH_INTERVAL_MS,
)
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
    log_dir = DATA_LAKE_ROOT / "operations" / "desktop" / "logs"
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
        logging.basicConfig(
            filename=log_dir / "lionare_desktop.log",
            level=logging.INFO,
            format="%(asctime)s %(levelname)s %(message)s",
        )
    except OSError:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s %(levelname)s %(message)s",
        )


class LionareMainWindow(QMainWindow):
    """Native Lionare workstation connected to the existing local API."""

    WORKSPACES: dict[str, set[str]] = {
        "DASHBOARD": {"global", "company", "watchlist", "pulse", "portfolio", "performance", "news", "quant", "data", "system"},
        "MARKETS": {"global", "watchlist", "pulse", "system"},
        "EQUITY": {"company", "watchlist", "quant", "system"},
        "PORTFOLIO": {"portfolio", "performance", "watchlist", "system"},
        "NEWS": {"news", "system"},
        "QUANT LAB": {"quant", "data", "watchlist", "system"},
        "DATA LAKE": {"data", "system"},
        "SYSTEM": {"system", "data"},
    }

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION}")
        self.resize(1680, 960)
        self.setMinimumSize(QSize(1180, 720))
        self.setDockNestingEnabled(True)
        self.setDockOptions(
            QMainWindow.DockOption.AllowNestedDocks
            | QMainWindow.DockOption.AllowTabbedDocks
            | QMainWindow.DockOption.AnimatedDocks
            | QMainWindow.DockOption.GroupedDragging
        )

        self.settings = QSettings("Lionex", "LionareTerminal")
        self.backend = BackendClient(API_BASE_URL, self)
        self.backend.received.connect(self._on_backend_data)
        self.backend.failed.connect(self._on_backend_error)
        self._backend_online = False
        self._latest_overview: dict[str, Any] = {}
        self._last_health: dict[str, Any] = {}

        self._build_menu()
        self._build_header()
        self._build_panels()
        self._build_status_bar()
        self._apply_theme()

        # Keep a known-good layout to support Reset Workspace.
        self._default_geometry = self.saveGeometry()
        self._default_state = self.saveState(1)
        self._restore_window_state()

        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.refresh_all)
        self.refresh_timer.start(REFRESH_INTERVAL_MS)

        self.clock_timer = QTimer(self)
        self.clock_timer.timeout.connect(self._update_clock)
        self.clock_timer.start(1000)
        self._update_clock()
        self.refresh_all()
        logging.info("Lionare desktop started; API=%s; data_lake=%s", API_BASE_URL, DATA_LAKE_ROOT)

    def _build_menu(self) -> None:
        file_menu = self.menuBar().addMenu("File")
        refresh_action = QAction("Refresh data", self)
        refresh_action.setShortcut("F5")
        refresh_action.triggered.connect(self.refresh_all)
        file_menu.addAction(refresh_action)

        save_action = QAction("Save workspace layout", self)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self.save_layout)
        file_menu.addAction(save_action)
        file_menu.addSeparator()

        exit_action = QAction("Exit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        self.view_menu = self.menuBar().addMenu("View")
        reset_action = QAction("Reset default layout", self)
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
        header = QToolBar("Terminal Header", self)
        header.setObjectName("headerToolbar")
        header.setMovable(False)
        header.setFloatable(False)
        header.setIconSize(QSize(16, 16))
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, header)

        brand = QLabel("  LIONARE")
        brand.setObjectName("brandMark")
        header.addWidget(brand)
        descriptor = QLabel("  FINANCIAL INTELLIGENCE")
        descriptor.setObjectName("brandDescriptor")
        header.addWidget(descriptor)

        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        header.addWidget(spacer)
        self.node_badge = QLabel("● ENGINE CHECKING")
        self.node_badge.setObjectName("statusWarn")
        header.addWidget(self.node_badge)
        self.clock_label = QLabel("  --:--:--  ")
        self.clock_label.setObjectName("clockLabel")
        header.addWidget(self.clock_label)

        ticker = QToolBar("Market Ticker", self)
        ticker.setObjectName("tickerToolbar")
        ticker.setMovable(False)
        ticker.setFloatable(False)
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, ticker)
        ticker.addWidget(QLabel("REFERENCE WATCH  │  "))
        self.ticker_labels: list[QLabel] = []
        for symbol in ("AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "JPM", "XOM", "SPX", "NDX", "NIFTY"):
            label = QLabel(f"{symbol}   —   ")
            label.setObjectName("tickerItem")
            ticker.addWidget(label)
            self.ticker_labels.append(label)
        ticker.addSeparator()
        refresh_btn = QPushButton("REFRESH")
        refresh_btn.clicked.connect(self.refresh_all)
        ticker.addWidget(refresh_btn)

        nav = QToolBar("Workspaces", self)
        nav.setObjectName("navToolbar")
        nav.setMovable(False)
        nav.setFloatable(False)
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, nav)
        self.nav_group = QButtonGroup(self)
        self.nav_group.setExclusive(True)
        self.nav_buttons: dict[str, QPushButton] = {}
        for name in self.WORKSPACES:
            button = QPushButton(name)
            button.setCheckable(True)
            button.clicked.connect(lambda checked=False, workspace=name: self.activate_workspace(workspace))
            nav.addWidget(button)
            self.nav_group.addButton(button)
            self.nav_buttons[name] = button
        self.nav_buttons["DASHBOARD"].setChecked(True)

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
        self.addDockWidget(area, dock)
        self.docks[key] = dock
        self.view_menu.addAction(dock.toggleViewAction())
        return dock

    def _build_panels(self) -> None:
        self.chart_workspace = ChartWorkspace()
        self.setCentralWidget(self.chart_workspace)
        self.docks: dict[str, QDockWidget] = {}

        self.global_panel = GlobalMarketsPanel()
        self.company_panel = CompanyResearchPanel()
        self.company_panel.symbol_changed.connect(self._request_company)
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
        self.quant_panel = QuantPanel(lqie_available, "PYTRENDLINE COMPATIBILITY FIX PENDING")
        self.data_panel = DataLakePanel()
        self.system_panel = SystemPanel(API_BASE_URL)

        self._add_dock("global", "GLOBAL MARKETS", self.global_panel, Qt.DockWidgetArea.LeftDockWidgetArea)
        self._add_dock("company", "COMPANY RESEARCH", self.company_panel, Qt.DockWidgetArea.LeftDockWidgetArea)
        self._add_dock("watchlist", "WATCHLIST", self.watchlist_panel, Qt.DockWidgetArea.RightDockWidgetArea)
        self._add_dock("pulse", "MARKET PULSE", self.pulse_panel, Qt.DockWidgetArea.RightDockWidgetArea)
        self._add_dock("portfolio", "PORTFOLIO SUMMARY", self.portfolio_panel, Qt.DockWidgetArea.BottomDockWidgetArea)
        self._add_dock("performance", "PERFORMANCE TRACKER", self.performance_panel, Qt.DockWidgetArea.BottomDockWidgetArea)
        self._add_dock("news", "NEWS & EVENTS", self.news_panel, Qt.DockWidgetArea.BottomDockWidgetArea)
        self._add_dock("quant", "LQIE QUANT LAB", self.quant_panel, Qt.DockWidgetArea.LeftDockWidgetArea)
        self._add_dock("data", "DATA LAKE", self.data_panel, Qt.DockWidgetArea.LeftDockWidgetArea)
        self._add_dock("system", "SYSTEM STATUS", self.system_panel, Qt.DockWidgetArea.RightDockWidgetArea)

        self.splitDockWidget(self.docks["global"], self.docks["company"], Qt.Orientation.Vertical)
        self.splitDockWidget(self.docks["company"], self.docks["quant"], Qt.Orientation.Vertical)
        self.splitDockWidget(self.docks["quant"], self.docks["data"], Qt.Orientation.Vertical)
        self.splitDockWidget(self.docks["watchlist"], self.docks["pulse"], Qt.Orientation.Vertical)
        self.splitDockWidget(self.docks["pulse"], self.docks["system"], Qt.Orientation.Vertical)
        self.splitDockWidget(self.docks["portfolio"], self.docks["performance"], Qt.Orientation.Horizontal)
        self.splitDockWidget(self.docks["performance"], self.docks["news"], Qt.Orientation.Horizontal)
        self.resizeDocks(
            [self.docks["global"], self.docks["watchlist"], self.docks["pulse"]],
            [260, 360, 260],
            Qt.Orientation.Horizontal,
        )
        self.resizeDocks(
            [self.docks["portfolio"], self.docks["performance"], self.docks["news"]],
            [260, 300, 500],
            Qt.Orientation.Horizontal,
        )
        self._request_company(str(self.company_panel.selector.currentData() or "AAPL"))

    def _build_status_bar(self) -> None:
        self.status = self.statusBar()
        self.status.showMessage("READY · LOCAL WORKSTATION · MARKET PRICE FEED NOT CONNECTED")
        self.status.setObjectName("terminalStatusBar")

    def _apply_theme(self) -> None:
        self.setStyleSheet(r"""
            QMainWindow, QWidget { background: #0b1018; color: #dce6f1; font-family: 'Segoe UI', 'Arial'; font-size: 9pt; }
            QMenuBar { background: #080c12; color: #aebdce; border-bottom: 1px solid #1c2a38; padding: 3px 8px; }
            QMenuBar::item { padding: 5px 12px; background: transparent; }
            QMenuBar::item:selected { background: #182635; color: #ffffff; }
            QMenu { background: #101925; border: 1px solid #26394a; }
            QMenu::item { padding: 7px 22px; }
            QMenu::item:selected { background: #1b3041; }
            QToolBar { background: #090e15; border: 0; spacing: 8px; padding: 5px 9px; }
            QToolBar#headerToolbar { border-bottom: 1px solid #1e2b38; }
            QToolBar#tickerToolbar { background: #0d141e; border-bottom: 1px solid #1e2b38; }
            QToolBar#navToolbar { background: #0b111a; border-bottom: 1px solid #243343; }
            QLabel#brandMark { color: #35d5b0; font-size: 19pt; font-weight: 800; letter-spacing: 2px; }
            QLabel#brandDescriptor { color: #7890a8; font-size: 8pt; letter-spacing: 2px; }
            QLabel#tickerItem { color: #9aafc3; font-family: Consolas, monospace; font-size: 8pt; padding: 2px 7px; }
            QLabel#clockLabel { color: #e5a34f; font-family: Consolas, monospace; font-weight: 700; }
            QLabel#statusWarn { color: #e6a84c; font-family: Consolas, monospace; font-size: 8pt; }
            QLabel#statusGood { color: #39d3a8; font-family: Consolas, monospace; font-size: 8pt; }
            QPushButton { background: #111c28; color: #b9c8d8; border: 1px solid #243547; border-radius: 3px; padding: 6px 10px; }
            QPushButton:hover { background: #1a2b3b; border-color: #39c9a6; color: #ffffff; }
            QPushButton:checked { background: #173329; color: #42dfb0; border: 1px solid #2bba91; }
            QDockWidget { color: #c7d7e7; font-weight: 700; }
            QDockWidget::title { background: #101925; padding: 7px 9px; border: 1px solid #253547; border-bottom: 1px solid #2e4255; }
            QWidget#panelBody { background: #0e1722; }
            QLabel#panelHeading { color: #e5edf6; font-weight: 700; letter-spacing: 1px; }
            QLabel#panelMeta { color: #6f8aa5; font-family: Consolas, monospace; font-size: 7pt; }
            QLabel#mutedText { color: #8397aa; }
            QLabel#goodText { color: #37d4a7; }
            QLabel#warnText { color: #e6a34a; }
            QTableWidget, QListWidget { background: #0c141e; alternate-background-color: #101b27; color: #cbd8e5; border: 1px solid #1d2d3d; selection-background-color: #183747; selection-color: #ffffff; }
            QHeaderView::section { background: #111d29; color: #829bb2; border: 0; border-bottom: 1px solid #26384a; padding: 6px; font-size: 8pt; }
            QTableWidget::item { padding: 4px; border-bottom: 1px solid #172636; }
            QListWidget::item { padding: 9px 7px; border-bottom: 1px solid #1a2a39; }
            QFrame#chartWorkspace { background: #0e1722; border: 1px solid #25394a; border-radius: 4px; }
            QLabel#chartTitle { color: #e9f1f8; font-weight: 700; letter-spacing: 2px; }
            QLabel#metricBlock { background: #132131; color: #dce8f3; border: 1px solid #24384a; border-radius: 3px; padding: 8px; font-family: Consolas, monospace; }
            QStatusBar { background: #080c12; color: #73a1a8; border-top: 1px solid #263647; font-family: Consolas, monospace; font-size: 8pt; }
            QScrollBar:vertical { background: #0b1118; width: 10px; }
            QScrollBar::handle:vertical { background: #283a4b; min-height: 24px; border-radius: 4px; }
        """)

    def _update_clock(self) -> None:
        self.clock_label.setText("  " + datetime.now().astimezone().strftime("%d %b %y  %H:%M:%S") + "  ")

    def _request_company(self, symbol: str) -> None:
        symbol = (symbol or "AAPL").strip().upper()
        self.backend.get(f"/api/company?symbol={quote(symbol)}")

    def refresh_all(self) -> None:
        # These routes exist in the inspected server.py. There is deliberately no
        # /api/datasets request: dataset inventory is included in /api/overview.
        for endpoint in ("/api/health", "/api/overview", "/api/companies", "/api/news"):
            self.backend.get(endpoint)
        self._request_company(str(self.company_panel.selector.currentData() or "AAPL"))
        self.status.showMessage("REFRESHING · LOCAL API · PRICE FEED NOT CONNECTED", 2500)

    def _on_backend_data(self, path: str, payload: Any) -> None:
        if path in ("/api/health", "/api/overview"):
            self._backend_online = True
            self.node_badge.setText("● ENGINE ONLINE")
            self.node_badge.setObjectName("statusGood")
            self.node_badge.style().unpolish(self.node_badge)
            self.node_badge.style().polish(self.node_badge)
            self.system_panel.set_backend(True, "LOCAL API RESPONDING")

        if path == "/api/health":
            self._last_health = payload if isinstance(payload, dict) else {}
            self.system_panel.update_health(self._last_health)
        elif path == "/api/overview":
            self._latest_overview = payload if isinstance(payload, dict) else {}
            self.data_panel.update_overview(self._latest_overview)
            self.system_panel.update_overview(self._latest_overview)
        elif path == "/api/companies":
            self.watchlist_panel.update_companies(payload)
        elif path == "/api/company":
            self.company_panel.update_company(payload)
        elif path == "/api/news":
            self.news_panel.update_news(payload)

    def _on_backend_error(self, path: str, message: str) -> None:
        logging.warning("Backend request failed: %s: %s", path, message)
        if path in ("/api/health", "/api/overview"):
            self._backend_online = False
            self.node_badge.setText("● ENGINE OFFLINE")
            self.node_badge.setObjectName("statusWarn")
            self.node_badge.style().unpolish(self.node_badge)
            self.node_badge.style().polish(self.node_badge)
            self.system_panel.set_backend(False, message)
            self.status.showMessage(f"BACKEND OFFLINE · {message}", 8000)
        elif path == "/api/company":
            self.company_panel.set_error(message)
        elif path == "/api/news":
            self.news_panel.set_error(message)

    def activate_workspace(self, workspace: str) -> None:
        workspace = workspace.upper()
        visible = self.WORKSPACES.get(workspace, self.WORKSPACES["DASHBOARD"])
        for key, dock in self.docks.items():
            dock.setVisible(key in visible)
        button = self.nav_buttons.get(workspace)
        if button and not button.isChecked():
            button.setChecked(True)
        self.status.showMessage(f"WORKSPACE · {workspace} · PANELS CAN BE REARRANGED", 4000)

    def save_layout(self) -> None:
        self.settings.setValue("window/geometry", self.saveGeometry())
        self.settings.setValue("window/state_v1", self.saveState(1))
        self.settings.setValue("window/version", APP_VERSION)
        self.status.showMessage("WORKSPACE LAYOUT SAVED", 3000)

    def _restore_window_state(self) -> None:
        saved_version = str(self.settings.value("window/version", ""))
        geometry = self.settings.value("window/geometry")
        state = self.settings.value("window/state_v1")
        if saved_version == APP_VERSION and geometry and state:
            self.restoreGeometry(geometry)
            self.restoreState(state, 1)

    def reset_layout(self) -> None:
        self.restoreGeometry(self._default_geometry)
        self.restoreState(self._default_state, 1)
        self.activate_workspace("DASHBOARD")
        self.save_layout()
        self.status.showMessage("DEFAULT WORKSPACE RESTORED", 3000)

    def _show_about(self) -> None:
        QMessageBox.about(
            self,
            "About Lionare",
            f"<b>{APP_NAME} {APP_VERSION}</b><br><br>Native financial workstation.<br>Data and quantitative services run separately from this desktop interface.",
        )

    def closeEvent(self, event: Any) -> None:  # noqa: N802 - Qt override
        self.save_layout()
        logging.info("Lionare desktop closed")
        event.accept()


def run() -> int:
    _configure_logging()
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName("Lionex")
    window = LionareMainWindow()
    window.show()
    return app.exec()
