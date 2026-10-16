{{ config(partition_by=day_partition('added_at'), cluster_by=['event_root_code']) }}

-- One row per event. GDELT can send the same event again in a later file,
-- so keep the newest copy.
select
    GlobalEventID as event_id,
    {{ parse_gdelt_ts('DateAdded') }} as added_at,
    EventCode as event_code,
    EventRootCode as event_root_code,
    QuadClass as quad_class,
    GoldsteinScale as goldstein_scale,
    IsRootEvent = 1 as is_root_event,
    Actor1Name as actor1_name,
    Actor1CountryCode as actor1_country,
    Actor2Name as actor2_name,
    Actor2CountryCode as actor2_country,
    ActionGeo_FullName as action_place,
    ActionGeo_CountryCode as action_country,
    NumArticles as num_articles,
    AvgTone as avg_tone,
    SourceURL as source_url
from {{ source('gdelt', 'raw_gdelt_events') }}
where GlobalEventID is not null
qualify row_number() over (partition by GlobalEventID order by DateAdded desc, source_file desc, SourceURL) = 1
