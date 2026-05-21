{{ config(
    materialized='table',
    unique_key='gold_id',
    tags=['gold']
) }}

with validated_data as (
    select * from {{ ref('silver_github_events') }}
    where validation_status = 'VALID'
),

aggregated as (
    select
        repo_name,
        created_at::date as activity_date,
        count(*) as total_events,
        sum(case when event_type = 'PushEvent' then 1 else 0 end) as push_events,
        sum(case when event_type = 'PullRequestEvent' then 1 else 0 end) as pull_request_events,
        sum(case when event_type = 'IssueCommentEvent' then 1 else 0 end) as issue_comment_events,
        count(distinct actor_login) as distinct_actors,
        max(ingested_at) as last_ingested_at,
        extract(epoch from avg(ingested_at - created_at)) as processing_latency_seconds
    from validated_data
    group by repo_name, created_at::date
),

final as (
    select
        repo_name,
        activity_date,
        total_events,
        push_events,
        pull_request_events,
        issue_comment_events,
        distinct_actors,
        processing_latency_seconds,
        last_ingested_at,
        (total_events - lag(total_events, 7) over (partition by repo_name order by activity_date))::double precision / 
            nullif(lag(total_events, 7) over (partition by repo_name order by activity_date), 0) as events_deviation_pct
    from aggregated
)

select
    {{ dbt_utils.generate_surrogate_key(['repo_name', 'activity_date']) }} as gold_id,
    repo_name,
    activity_date,
    total_events,
    push_events,
    pull_request_events,
    issue_comment_events,
    distinct_actors,
    events_deviation_pct,
    processing_latency_seconds,
    last_ingested_at
from final
