from datetime import date

from lqie.data.schema import normalize_ohlcv_records


class OpenBBCBOEAdapter:
    """Optional OpenBB adapter for CBOE historical OHLCV data."""

    def __init__(self, client=None):
        self.client = client

    def fetch_ohlcv(self, symbol, start_date, end_date):
        if not symbol or not symbol.strip():
            raise ValueError("symbol cannot be empty")

        start = date.fromisoformat(str(start_date)[:10])
        end = date.fromisoformat(str(end_date)[:10])

        if start > end:
            raise ValueError("start_date cannot be after end_date")

        client = self.client

        if client is None:
            try:
                from openbb import obb
                client = obb
            except ImportError as exc:
                raise RuntimeError(
                    "OpenBB is not installed. Install its provider packages."
                ) from exc

        result = client.cboe.equity.historical(
            symbol=symbol.upper(),
            start_date=start.isoformat(),
            end_date=end.isoformat(),
        )

        frame = result.to_dataframe()

        if frame.empty:
            raise ValueError(f"No data returned for {symbol}")

        frame = frame.reset_index()
        records = frame.to_dict(orient="records")

        provider = getattr(result, "provider", "cboe") or "cboe"

        return normalize_ohlcv_records(
            symbol=symbol,
            records=records,
            source=provider,
        )
