-- Staging keeps one row per event and web article. Returns a row on mismatch.
with raw as (
    select count(*) as n from (
        select distinct GlobalEventID, MentionIdentifier
        from {{ source('gdelt', 'raw_gdelt_mentions') }}
        where MentionType = 1 and MentionSourceName is not null and MentionIdentifier is not null
    ) d
),
stg as (
    select count(*) as n from {{ ref('stg_gdelt_mentions') }}
)
select raw.n as raw_mentions, stg.n as staged_mentions
from raw cross join stg
where raw.n != stg.n
