from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    kafka_bootstrap: str
    kafka_topic: str
    symbols: tuple[str, ...]
    binance_ws_base: str
    log_level: str
    min_interval_sec: float

    @classmethod
    def from_env(cls) -> "Config":
        raw_symbols = os.environ.get("BINANCE_SYMBOLS", "btcusdt")
        symbols = tuple(s.strip().upper() for s in raw_symbols.split(",") if s.strip())
        if not symbols:
            raise ValueError("BINANCE_SYMBOLS must contain at least one symbol")

        return cls(
            kafka_bootstrap=os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092"),
            kafka_topic=os.environ.get("KAFKA_TOPIC_RAW_TRADES", "raw_trades"),
            symbols=symbols,
            binance_ws_base=os.environ.get(
                "BINANCE_WS_BASE", "wss://stream.binance.com:9443"
            ),
            log_level=os.environ.get("LOG_LEVEL", "INFO").upper(),
            min_interval_sec=float(os.environ.get("PRODUCER_MIN_INTERVAL_SEC", "0")),
        )
