{{ config(
    materialized='table',
    unique_key='silver_id',
    on_schema_change='fail',
    tags=['silver']
) }}

with source_data as (
    select * from {{ ref('bronze_fda_events') }}
),

deduplicated as (
    select
        *,
        row_number() over (
            partition by pipeline_run_id, receipt_date, drug_name
            order by ingested_at desc
        ) as row_num
    from source_data
),

filtered as (
    select
        id,
        pipeline_run_id,
        receipt_date,
        serious,
        reporter_country,
        drug_name,
        reaction_description,
        seriousness_hospitalization,
        raw_payload,
        ingested_at
    from deduplicated
    where row_num = 1
      and receipt_date is not null
),

validated as (
    select
        *,
        case
            when receipt_date::date > current_date then 'INVALID_RECEIPT_DATE'
            when serious not in ('1', '2') and serious is not null then 'INVALID_SERIOUS_VALUE'
            when serious is null then 'WARNING_MISSING_SERIOUS'
            else 'VALID'
        end as validation_status
    from filtered
)

select
    {{ dbt_utils.generate_surrogate_key(['pipeline_run_id', 'receipt_date', 'drug_name']) }} as silver_id,
    id as bronze_id,
    pipeline_run_id,
    receipt_date,
    serious,
    reporter_country,
    drug_name,
    reaction_description,
    seriousness_hospitalization,
    raw_payload,
    ingested_at,
    validation_status
from validated
