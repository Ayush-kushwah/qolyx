SELECT *
FROM {{ ref('bronze_financial_candles') }}
WHERE candle_timestamp > CURRENT_TIMESTAMP + INTERVAL '1 hour'
