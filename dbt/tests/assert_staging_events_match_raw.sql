-- Staging should keep exactly one row per distinct raw event ID. Returns a row on mismatch.
with raw as (
    select count(distinct GlobalEventID) as n from {{ source('gdelt', 'raw_gdelt_events') }}
),
stg as (
    select count(*) as n from {{ ref('stg_gdelt_events') }}
)
select raw.n as raw_events, stg.n as staged_events
from raw cross join stg
where raw.n != stg.n
