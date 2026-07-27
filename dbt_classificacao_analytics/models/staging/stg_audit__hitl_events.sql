select *
from {{ source('audit', 'hitl_events') }}