{{ config(
    materialized='table',
    unique_key='id',
    tags=['bronze']
) }}

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
from {{ source('qolyx_source', 'bronze_github_events') }}
where ingested_at > current_timestamp - interval '24 hours'
