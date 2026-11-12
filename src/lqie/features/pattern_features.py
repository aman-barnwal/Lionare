"""Convert pattern detections into model-ready numeric features."""


def build_pattern_feature_row(analysis: dict) -> dict:
    detections = analysis.get("detections", [])

    row = {
        "symbol": analysis["symbol"],
        "timeframe": analysis["timeframe"],
        "bars_analysed": analysis["bars_analysed"],
        "detection_count": len(detections),
    }

    for category in (
        "candlestick",
        "trendline",
        "harmonic",
        "regime",
    ):
        selected = [
            item for item in detections
            if item["category"] == category
        ]

        row[f"{category}_count"] = len(selected)

        row[f"{category}_bullish_count"] = sum(
            item["direction"] == "bullish"
            for item in selected
        )

        row[f"{category}_bearish_count"] = sum(
            item["direction"] == "bearish"
            for item in selected
        )

        row[f"{category}_prediction_count"] = sum(
            bool(item["is_prediction"])
            for item in selected
        )

    for name, value in analysis.get("indicators", {}).items():
        if isinstance(value, dict):
            for child, child_value in value.items():
                row[f"indicator_{name}_{child}"] = child_value
        else:
            row[f"indicator_{name}"] = value

    return row
