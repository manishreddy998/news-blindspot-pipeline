{{ config(partition_by=day_partition('mentioned_at'), cluster_by=['outlet_domain']) }}

-- One row per article mention of an event. Only web articles (MentionType 1),
-- since the other types have no outlet domain we can rate.
select
    GlobalEventID as event_id,
    {{ parse_gdelt_ts('MentionTimeDate') }} as mentioned_at,
    lower(MentionSourceName) as outlet_domain,
    MentionIdentifier as article_url,
    Confidence as confidence
from {{ source('gdelt', 'raw_gdelt_mentions') }}
where MentionType = 1
  and MentionSourceName is not null
  and MentionIdentifier is not null
qualify row_number() over (partition by GlobalEventID, MentionIdentifier order by MentionTimeDate, MentionSourceName, Confidence desc) = 1
