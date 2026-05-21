{{ config(
    materialized='table',
    unique_key='gold_id',
    tags=['gold']
) }}

with validated_data as (
    select * from {{ ref('silver_fda_events') }}
    where validation_status in ('VALID', 'WARNING_MISSING_SERIOUS')
),

aggregated as (
    select
        drug_name,
        receipt_date::date as receipt_date,
        count(*) as total_cases,
        sum(case when cast(serious as varchar) = '1' then 1 else 0 end) as serious_cases,
        sum(case when cast(seriousness_hospitalization as varchar) = '1' then 1 else 0 end) as hospitalization_cases,
        max(ingested_at) as last_ingested_at,
        extract(epoch from avg(ingested_at - receipt_date::timestamp)) as processing_latency_seconds
    from validated_data
    group by drug_name, receipt_date::date
),

final as (
    select
        drug_name,
        receipt_date,
        total_cases,
        serious_cases,
        hospitalization_cases,
        serious_cases::double precision / nullif(total_cases, 0) as serious_ratio,
        hospitalization_cases::double precision / nullif(total_cases, 0) as hospitalization_ratio,
        processing_latency_seconds,
        last_ingested_at,
        (total_cases - lag(total_cases, 7) over (partition by drug_name order by receipt_date))::double precision / 
            nullif(lag(total_cases, 7) over (partition by drug_name order by receipt_date), 0) as cases_deviation_pct
    from aggregated
)

select
    {{ dbt_utils.generate_surrogate_key(['drug_name', 'receipt_date']) }} as gold_id,
    drug_name,
    receipt_date,
    total_cases,
    serious_cases,
    hospitalization_cases,
    serious_ratio,
    hospitalization_ratio,
    cases_deviation_pct,
    processing_latency_seconds,
    last_ingested_at
from final
