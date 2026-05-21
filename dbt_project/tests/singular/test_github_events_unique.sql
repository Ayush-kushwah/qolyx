select
    event_id,
    count(*)
from {{ ref('silver_github_events') }}
group by event_id
having count(*) > 1
