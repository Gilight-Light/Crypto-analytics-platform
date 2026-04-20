# dbt

SQL transformations over the Silver Iceberg layer, landed into `iceberg.gold.*`
via Trino.

## Layout

```
dbt/
├── dbt_project.yml
├── profiles.yml               # Trino connection (host=trino:8080, catalog=iceberg)
└── models/
    ├── staging/
    │   ├── sources.yml        # Declares silver.trades as a dbt source
    │   └── stg_trades.sql     # View over silver.trades
    └── marts/
        └── fact_trades_1h.sql # 1h OHLCV fact → iceberg.gold.*
```

## Running

Requires Trino + HMS + Silver tables up (profile `serving` includes Trino).

```bash
docker run --rm --network platform-net \
  -v $PWD/dbt:/dbt \
  -e DBT_PROFILES_DIR=/dbt \
  ghcr.io/dbt-labs/dbt-trino:1.8.4 \
  run --project-dir /dbt
```

## Tests (planned)

- `stg_trades`: `unique` + `not_null` on `(symbol, trade_id)`
- `fact_trades_1h`: `not_null` on primary dimensions
