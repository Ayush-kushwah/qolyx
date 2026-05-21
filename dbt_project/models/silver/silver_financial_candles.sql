{{ config(
    materialized='table',
    unique_key='silver_id',
    on_schema_change='fail',
    tags=['silver']
) }}

with source_data as (
    select * from {{ ref('bronze_financial_candles') }}
),

deduplicated as (
    select
        *,
        row_number() over (
            partition by pipeline_run_id, symbol, candle_timestamp
            order by ingested_at desc
        ) as row_num
    from source_data
),

filtered as (
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
    from deduplicated
    where row_num = 1
      and open_price is not null
      and high_price is not null
      and low_price is not null
      and volume > 0
),

validated as (
    select
        *,
        case
            when not (high_price >= low_price) then 'INVALID_HIGH_LOW'
            when not (close_price >= low_price and close_price <= high_price) then 'INVALID_CLOSE'
            else 'VALID'
        end as validation_status
    from filtered
)

select
    {{ dbt_utils.generate_surrogate_key(['pipeline_run_id', 'symbol', 'candle_timestamp']) }} as silver_id,
    id as bronze_id,
    pipeline_run_id,
    symbol,
    open_price,
    high_price,
    low_price,
    close_price,
    volume,
    candle_timestamp,
    ingested_at,
    validation_status
from validated
