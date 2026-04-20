# Binance WebSocket → Kafka producer

Long-running service that subscribes to Binance `@trade` streams for N symbols
on a single combined WebSocket and publishes normalized trade events to Kafka.

## Files

| File | Purpose |
|---|---|
| `producer.py` | Async entry point (WS consumer + Kafka producer + reconnect loop). |
| `config.py`   | Env var parsing (dataclass). |
| `schema.py`   | Binance → internal trade schema normalization. |
| `Dockerfile`  | `python:3.11-slim` + non-root user. |

## Kafka message shape

Key: `"<SYMBOL>:<TRADE_ID>"` — deterministic so retries don't duplicate, and
same-symbol trades land on the same partition (preserves per-symbol ordering).

Value (JSON):

```json
{
  "trade_id": 123456789,
  "symbol": "BTCUSDT",
  "price": 67234.12,
  "qty": 0.0015,
  "quote_qty": 100.8512,
  "trade_time_ms": 1713500000000,
  "event_time_ms": 1713500000001,
  "is_buyer_maker": false,
  "ingested_at": "2026-04-20T00:00:00.000Z"
}
```

`is_buyer_maker=true` means the taker was a seller (buyer had a resting order).

## Reliability

- Keyed produce pins same-symbol trades to the same partition (per-symbol order).
- `enable_idempotence=True`, `acks=all` avoids in-session duplicates.
- Exponential backoff reconnect (1s → 60s cap). Binance rotates WS every 24h —
  clean close resets backoff to 1s.
- `SIGINT` / `SIGTERM` → flush Kafka → close WS.
- JSON logs on stdout; progress stats every 100 trades.

## Env vars

| Var | Default | Notes |
|---|---|---|
| `KAFKA_BOOTSTRAP_SERVERS` | `kafka:9092` | Internal (compose network) |
| `KAFKA_TOPIC_RAW_TRADES` | `raw_trades` | Must exist — `kafka-init` creates it |
| `BINANCE_SYMBOLS` | `btcusdt` | Comma-separated |
| `BINANCE_WS_BASE` | `wss://stream.binance.com:9443` | Override for testnet |
| `LOG_LEVEL` | `INFO` | |
