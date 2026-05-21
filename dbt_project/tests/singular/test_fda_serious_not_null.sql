select *
from {{ ref('silver_fda_events') }}
where validation_status = 'VALID'
  and serious is null
