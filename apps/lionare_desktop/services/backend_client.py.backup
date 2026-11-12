from __future__ import annotations

import json
from typing import Any

from PySide6.QtCore import QObject, QUrl, Signal
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkRequest


class BackendClient(QObject):
    """Asynchronous JSON client with actionable network diagnostics."""

    received = Signal(str, object)
    failed = Signal(str, str)

    def __init__(self, base_url: str, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.base_url = base_url.rstrip("/")
        self.manager = QNetworkAccessManager(self)

    def get(self, path: str) -> None:
        clean_path = "/" + path.lstrip("/")
        url = QUrl(self.base_url + clean_path)
        request = QNetworkRequest(url)
        request.setRawHeader(b"Accept", b"application/json")
        request.setTransferTimeout(7_000)
        reply = self.manager.get(request)
        reply.setProperty("lionare_path", clean_path)
        reply.setProperty("lionare_url", url.toString())
        reply.finished.connect(lambda current=reply: self._finish(current))

    def _finish(self, reply: Any) -> None:
        path = str(reply.property("lionare_path") or "unknown")
        url = str(reply.property("lionare_url") or self.base_url)
        try:
            status = reply.attribute(QNetworkRequest.Attribute.HttpStatusCodeAttribute)
            if reply.error():
                code = int(reply.error())
                detail = reply.errorString() or "No network error detail supplied"
                suffix = f"HTTP {status}; " if status is not None else ""
                self.failed.emit(path, f"{suffix}Qt network error {code}: {detail} [{url}]")
                return

            raw = bytes(reply.readAll())
            try:
                payload = json.loads(raw.decode("utf-8")) if raw else {}
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                preview = raw[:180].decode("utf-8", errors="replace")
                self.failed.emit(path, f"Invalid JSON response: {exc}; body={preview!r}")
                return
            self.received.emit(path, payload)
        finally:
            reply.deleteLater()
