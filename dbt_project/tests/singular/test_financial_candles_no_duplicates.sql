select
    pipeline_run_id,
    symbol,
    candle_timestamp,
    count(*)
from {{ ref('silver_financial_candles') }}
group by pipeline_run_id, symbol, candle_timestamp
having count(*) > 1
