{{ config(
    materialized='table',
    unique_key='gold_id',
    tags=['gold']
) }}

with validated_data as (
    select * from {{ ref('silver_financial_candles') }}
    where validation_status = 'VALID'
),

aggregated as (
    select
        symbol,
        candle_timestamp::date as candle_date,
        avg(close_price) as avg_close_price,
        max(high_price) as max_high_price,
        min(low_price) as min_low_price,
        sum(volume) as total_volume,
        count(*) as candle_count,
        coalesce(stddev(close_price), 0) as price_volatility,
        coalesce(stddev(volume), 0) as volume_volatility,
        max(ingested_at) as last_ingested_at,
        extract(epoch from avg(ingested_at - candle_timestamp)) as processing_latency_seconds
    from validated_data
    group by symbol, candle_timestamp::date
),

final as (
    select
        symbol,
        candle_date,
        avg_close_price,
        max_high_price,
        min_low_price,
        total_volume,
        candle_count,
        price_volatility,
        volume_volatility,
        last_ingested_at,
        processing_latency_seconds,
        (total_volume - lag(total_volume, 30) over (partition by symbol order by candle_date)) / 
            nullif(lag(total_volume, 30) over (partition by symbol order by candle_date), 0) as volume_deviation_pct
    from aggregated
)

select
    {{ dbt_utils.generate_surrogate_key(['symbol', 'candle_date']) }} as gold_id,
    symbol,
    candle_date,
    avg_close_price,
    max_high_price,
    min_low_price,
    total_volume,
    candle_count,
    price_volatility,
    volume_volatility,
    volume_deviation_pct,
    processing_latency_seconds,
    last_ingested_at
from final
