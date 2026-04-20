from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, TypedDict


class Trade(TypedDict):
    trade_id: int
    symbol: str
    price: float
    qty: float
    quote_qty: float
    trade_time_ms: int
    event_time_ms: int
    is_buyer_maker: bool
    ingested_at: str


def _iso_utc_now() -> str:
    return (
        datetime.now(timezone.utc)
        .isoformat(timespec="milliseconds")
        .replace("+00:00", "Z")
    )


def normalize_trade(raw: dict[str, Any]) -> Trade:
    price = float(raw["p"])
    qty = float(raw["q"])
    return {
        "trade_id": int(raw["t"]),
        "symbol": raw["s"],
        "price": price,
        "qty": qty,
        "quote_qty": round(price * qty, 8),
        "trade_time_ms": int(raw["T"]),
        "event_time_ms": int(raw["E"]),
        "is_buyer_maker": bool(raw["m"]),
        "ingested_at": _iso_utc_now(),
    }
