{{ config(
    materialized='table',
    unique_key='id',
    tags=['bronze']
) }}

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
from {{ source('qolyx_source', 'bronze_fda_events') }}
where ingested_at > current_timestamp - interval '24 hours'
