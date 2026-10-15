-- One row per story with a readable label and article counts.
with ev as (
    select * from {{ ref('int_event_stories') }}
),

articles as (
    select
        ev.story_id,
        m.outlet_domain,
        m.article_url,
        m.mentioned_at
    from ev
    join {{ ref('stg_gdelt_mentions') }} m on m.event_id = ev.event_id
),

labels as (
    -- Use the place from the event with the most articles as the label.
    select story_id, story_day, event_root_code, actor_a, actor_b, action_place
    from ev
    qualify row_number() over (partition by story_id order by num_articles desc, event_id) = 1
)

select
    l.story_id,
    l.story_day,
    l.event_root_code,
    trim(l.actor_a || case when l.actor_a != '' and l.actor_b != '' then ' / ' else '' end || l.actor_b) as actors,
    l.action_place,
    count(distinct a.article_url) as articles,
    count(distinct a.outlet_domain) as outlets,
    min(a.mentioned_at) as first_seen_at,
    max(a.mentioned_at) as last_seen_at
from labels l
join articles a on a.story_id = l.story_id
group by 1, 2, 3, 4, 5
