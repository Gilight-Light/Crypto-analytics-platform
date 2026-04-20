"""Binance WebSocket -> Kafka producer."""
from __future__ import annotations

import asyncio
import json
import logging
import signal
import sys
import time

import structlog
import websockets
from aiokafka import AIOKafkaProducer
from websockets.exceptions import ConnectionClosed

from config import Config
from schema import normalize_trade


def _configure_logging(level: str) -> None:
    logging.basicConfig(level=level, stream=sys.stdout, format="%(message)s")
    structlog.configure(
        processors=[
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, level, logging.INFO)
        ),
    )


log = structlog.get_logger("binance_producer")


class BinanceTradeProducer:
    def __init__(self, config: Config) -> None:
        self.config = config
        self.producer: AIOKafkaProducer | None = None
        self.shutdown = asyncio.Event()
        self.stats = {"received": 0, "sent": 0, "throttled": 0, "errors": 0, "reconnects": 0}
        self._last_sent_ts: dict[str, float] = {}

    def _stream_url(self) -> str:
        streams = "/".join(f"{s.lower()}@trade" for s in self.config.symbols)
        return f"{self.config.binance_ws_base}/stream?streams={streams}"

    async def start(self) -> None:
        self.producer = AIOKafkaProducer(
            bootstrap_servers=self.config.kafka_bootstrap,
            acks="all",
            compression_type="gzip",
            linger_ms=50,
            enable_idempotence=True,
            key_serializer=lambda k: k.encode("utf-8") if isinstance(k, str) else k,
            value_serializer=lambda v: json.dumps(v, separators=(",", ":")).encode(
                "utf-8"
            ),
        )
        await self.producer.start()
        log.info(
            "kafka_producer_started",
            bootstrap=self.config.kafka_bootstrap,
            topic=self.config.kafka_topic,
        )

    async def stop(self) -> None:
        if self.producer is not None:
            await self.producer.flush()
            await self.producer.stop()
        log.info("shutdown_complete", **self.stats)

    async def _handle(self, raw: str) -> None:
        self.stats["received"] += 1
        try:
            envelope = json.loads(raw)
            payload = envelope.get("data", envelope)
            if payload.get("e") != "trade":
                return
            normalized = normalize_trade(payload)
        except (KeyError, ValueError, TypeError) as exc:
            self.stats["errors"] += 1
            log.warning("bad_message", error=str(exc), preview=raw[:200])
            return

        symbol = normalized["symbol"]
        if self.config.min_interval_sec > 0:
            now = time.monotonic()
            last = self._last_sent_ts.get(symbol, 0.0)
            if now - last < self.config.min_interval_sec:
                self.stats["throttled"] += 1
                return
            self._last_sent_ts[symbol] = now

        key = f"{symbol}:{normalized['trade_id']}"
        assert self.producer is not None
        await self.producer.send_and_wait(
            self.config.kafka_topic, value=normalized, key=key
        )
        self.stats["sent"] += 1

        if self.stats["sent"] % 50 == 0:
            log.info("progress", **self.stats)

    async def _run_ws(self) -> None:
        url = self._stream_url()
        log.info("ws_connecting", symbols=list(self.config.symbols))
        async with websockets.connect(
            url, ping_interval=20, ping_timeout=10, max_size=2**20
        ) as ws:
            log.info("ws_connected")
            async for msg in ws:
                if self.shutdown.is_set():
                    break
                await self._handle(msg)

    async def run(self) -> None:
        await self.start()
        backoff_s = 1
        max_backoff_s = 60

        while not self.shutdown.is_set():
            try:
                await self._run_ws()
                backoff_s = 1
            except ConnectionClosed as exc:
                log.warning("ws_closed", code=exc.code, reason=str(exc.reason))
            except (OSError, asyncio.TimeoutError) as exc:
                log.warning("ws_network_error", error=str(exc))
            except Exception:
                log.exception("ws_unexpected_error")

            if self.shutdown.is_set():
                break

            self.stats["reconnects"] += 1
            log.info(
                "reconnecting",
                wait_s=backoff_s,
                next_backoff_s=min(backoff_s * 2, max_backoff_s),
            )
            try:
                await asyncio.wait_for(self.shutdown.wait(), timeout=backoff_s)
                break
            except asyncio.TimeoutError:
                pass
            backoff_s = min(backoff_s * 2, max_backoff_s)

        await self.stop()


async def amain() -> None:
    config = Config.from_env()
    _configure_logging(config.log_level)
    log.info(
        "starting",
        symbols=list(config.symbols),
        kafka=config.kafka_bootstrap,
        topic=config.kafka_topic,
    )

    producer = BinanceTradeProducer(config)

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(
            sig,
            lambda s=sig: (
                log.info("signal_received", signal=s.name),
                producer.shutdown.set(),
            ),
        )

    await producer.run()


if __name__ == "__main__":
    asyncio.run(amain())
