{{ config(
    materialized='table',
    unique_key='id',
    tags=['bronze']
) }}

select
    id,
    pipeline_run_id,
    symbol,
    open_price,
    high_price,
    low_price,
    close_price,
    volume,
    candle_timestamp,
    ingested_at
from {{ source('qolyx_source', 'bronze_financial_candles') }}
where ingested_at > current_timestamp - interval '24 hours'
