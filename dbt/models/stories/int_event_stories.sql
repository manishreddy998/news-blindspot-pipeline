-- Map each event to a story.
--
-- A single GDELT event is too small to be a story: one article about a summit
-- produces many events (meet, praise, sign a deal), and two outlets covering
-- the same news often get different event IDs. So we group events that share
-- the same actors (in either order), the same kind of action (root CAMEO code),
-- the same place and the same UTC day. That is coarse, but it is cheap,
-- explainable and runs the same in DuckDB and BigQuery.
with events as (
    select * from {{ ref('stg_gdelt_events') }}
    where is_root_event
      and (actor1_name is not null or actor2_name is not null)
),

keyed as (
    select
        *,
        least(coalesce(actor1_name, ''), coalesce(actor2_name, '')) as actor_a,
        greatest(coalesce(actor1_name, ''), coalesce(actor2_name, '')) as actor_b,
        cast(cast(added_at as date) as {{ 'string' if target.type == 'bigquery' else 'varchar' }}) as story_day
    from events
)

select
    {{ hash_key("story_day || '|' || event_root_code || '|' || actor_a || '|' || actor_b || '|' || coalesce(action_country, '')") }} as story_id,
    event_id,
    story_day,
    event_root_code,
    actor_a,
    actor_b,
    action_place,
    action_country,
    num_articles
from keyed
