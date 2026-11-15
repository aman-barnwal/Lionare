from __future__ import annotations

import json
from typing import Any

from PySide6.QtCore import QObject, QUrl, Signal
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest


class BackendClient(QObject):
    """Asynchronous JSON client with safe PySide6 enum handling."""

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
        request.setTransferTimeout(8_000)
        reply = self.manager.get(request)
        reply.setProperty("lionare_path", clean_path)
        reply.setProperty("lionare_url", url.toString())
        reply.finished.connect(lambda current=reply: self._finish(current))

    def _finish(self, reply: QNetworkReply) -> None:
        path = str(reply.property("lionare_path") or "unknown")
        url = str(reply.property("lionare_url") or self.base_url)
        try:
            network_error = reply.error()
            no_error = QNetworkReply.NetworkError.NoError
            status = reply.attribute(QNetworkRequest.Attribute.HttpStatusCodeAttribute)
            if network_error != no_error:
                error_name = getattr(network_error, "name", str(network_error))
                error_value = getattr(network_error, "value", "")
                detail = reply.errorString() or error_name
                suffix = f"HTTP {status}; " if status is not None else ""
                code = f" (Qt {error_name}, code {error_value})" if error_value != "" else f" (Qt {error_name})"
                self.failed.emit(path, f"{suffix}{detail}{code} [{url}]")
                return

            raw = bytes(reply.readAll())
            try:
                payload = json.loads(raw.decode("utf-8")) if raw else {}
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                preview = raw[:180].decode("utf-8", errors="replace")
                self.failed.emit(path, f"Invalid JSON response: {exc}; body={preview!r} [{url}]")
                return
            self.received.emit(path, payload)
        except Exception as exc:
            self.failed.emit(path, f"{type(exc).__name__}: {exc} [{url}]")
        finally:
            reply.deleteLater()
