-- One row per story with a readable label and article counts.
with arts as (
    select * from {{ ref('int_article_stories') }}
),

ev as (
    select event_id, event_root_code, actor1_name, actor2_name, action_place
    from {{ ref('stg_gdelt_events') }}
),

-- The place, action and actors named most often across the story's articles.
place as (
    select story_id, action_place
    from (
        select a.story_id, e.action_place, count(distinct a.copy_key) as n
        from arts a join ev e on e.event_id = a.event_id
        where e.action_place is not null
        group by 1, 2
    ) p
    qualify row_number() over (partition by story_id order by n desc, action_place) = 1
),

actors as (
    select story_id, actors, event_root_code
    from (
        select
            a.story_id,
            e.event_root_code,
            trim(coalesce(e.actor1_name, '') || case when e.actor1_name is not null and e.actor2_name is not null
                 then ' / ' else '' end || coalesce(e.actor2_name, '')) as actors,
            count(distinct a.copy_key) as n
        from arts a join ev e on e.event_id = a.event_id
        group by 1, 2, 3
    ) x
    qualify row_number() over (partition by story_id order by n desc, actors) = 1
),

base as (
    select
        story_id,
        -- headline beats headline_via_event beats event
        case when count(case when grouped_by != 'event' then 1 end) > 0 then 'headline' else 'event' end as grouped_by,
        max(story_headline) as headline,
        count(distinct article_url) as articles,
        count(distinct copy_key) as unique_articles,
        count(distinct outlet_domain) as outlets,
        min(mentioned_at) as first_seen_at,
        max(mentioned_at) as last_seen_at
    from arts
    group by 1
)

select
    b.story_id,
    cast(cast(b.first_seen_at as date) as {{ 'string' if target.type == 'bigquery' else 'varchar' }}) as story_day,
    b.grouped_by,
    b.headline,
    ac.event_root_code,
    ac.actors,
    p.action_place,
    b.articles,
    b.unique_articles,
    b.outlets,
    b.first_seen_at,
    b.last_seen_at
from base b
left join place p on p.story_id = b.story_id
left join actors ac on ac.story_id = b.story_id
