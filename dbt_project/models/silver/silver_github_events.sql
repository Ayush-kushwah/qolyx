{{ config(
    materialized='table',
    unique_key='silver_id',
    on_schema_change='fail',
    tags=['silver']
) }}

with source_data as (
    select * from {{ ref('bronze_github_events') }}
),

deduplicated as (
    select
        *,
        row_number() over (
            partition by pipeline_run_id, event_id
            order by ingested_at desc
        ) as row_num
    from source_data
),

filtered as (
    select
        id,
        pipeline_run_id,
        event_id,
        event_type,
        actor_login,
        repo_name,
        payload_action,
        created_at,
        raw_payload,
        ingested_at
    from deduplicated
    where row_num = 1
      and event_id is not null
      and event_type is not null
),

validated as (
    select
        *,
        case
            when created_at > current_timestamp + interval '1 hour' then 'INVALID_CREATED_AT'
            else 'VALID'
        end as validation_status
    from filtered
)

select
    {{ dbt_utils.generate_surrogate_key(['pipeline_run_id', 'event_id']) }} as silver_id,
    id as bronze_id,
    pipeline_run_id,
    event_id,
    event_type,
    actor_login,
    repo_name,
    payload_action,
    created_at,
    raw_payload,
    ingested_at,
    validation_status
from validated
