from __future__ import annotations

import json
from typing import Any

from PySide6.QtCore import QObject, QUrl, Signal
from PySide6.QtNetwork import (
    QNetworkAccessManager,
    QNetworkReply,
    QNetworkRequest,
)


class BackendClient(QObject):
    """Asynchronous JSON client for the Lionare local API."""

    received = Signal(str, object)
    failed = Signal(str, str)

    def __init__(self, base_url: str, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.base_url = base_url.rstrip("/")
        self.manager = QNetworkAccessManager(self)

    def get(self, path: str) -> None:
        clean_path = "/" + path.lstrip("/")
        request = QNetworkRequest(QUrl(self.base_url + clean_path))
        request.setRawHeader(b"Accept", b"application/json")
        request.setTransferTimeout(8000)

        reply = self.manager.get(request)
        reply.setProperty("lionare_path", clean_path)
        reply.finished.connect(
            lambda current=reply: self._finish(current)
        )

    def _finish(self, reply: QNetworkReply) -> None:
        path = str(reply.property("lionare_path") or "unknown")

        try:
            error = reply.error()

            if error != QNetworkReply.NetworkError.NoError:
                error_name = getattr(error, "name", str(error))
                error_value = getattr(error, "value", None)
                detail = reply.errorString() or error_name
                url = reply.url().toString()

                if error_value is not None:
                    detail += f" (Qt {error_name}, code {error_value})"

                detail += f" | URL: {url}"
                self.failed.emit(path, detail)
                return

            raw = bytes(reply.readAll())

            try:
                payload = json.loads(raw.decode("utf-8")) if raw else {}
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                self.failed.emit(path, f"Invalid JSON response: {exc}")
                return

            self.received.emit(path, payload)

        except Exception as exc:
            self.failed.emit(
                path,
                f"{type(exc).__name__}: {exc}"
            )
        finally:
            reply.deleteLater()
