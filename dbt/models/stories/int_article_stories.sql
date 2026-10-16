-- Which story each article belongs to.
--
-- 1. Articles with a usable headline get their story from headline clustering (story_map).
-- 2. Articles without one (URLs like /article/12345) join the headline story that
--    shares the most GDELT events with them, since GDELT linked them to the same events.
-- 3. Anything left falls back to the event based grouping. Those stories have no
--    headline to check, so story_blindspots does not flag them.
with articles as (
    select distinct
        m.event_id,
        m.article_url,
        m.outlet_domain,
        m.mentioned_at,
        c.copy_key,
        c.is_syndicated
    from {{ ref('stg_gdelt_mentions') }} m
    join {{ ref('stg_article_copies') }} c
      on c.article_url = m.article_url and c.outlet_domain = m.outlet_domain
),

tagged as (
    select a.*, sm.story_id as headline_story, sm.story_headline
    from articles a
    left join {{ source('clusters', 'story_map') }} sm on sm.copy_key = a.copy_key
),

-- How strongly each event points to each headline story.
event_votes as (
    select event_id, headline_story, story_headline, count(distinct copy_key) as votes
    from tagged
    where headline_story is not null
    group by 1, 2, 3
),

borrowed as (
    select copy_key, headline_story, story_headline
    from (
        select t.copy_key, v.headline_story, v.story_headline, sum(v.votes) as votes
        from tagged t
        join event_votes v on v.event_id = t.event_id
        where t.headline_story is null
        group by 1, 2, 3
    ) x
    qualify row_number() over (partition by copy_key order by votes desc, headline_story) = 1
)

select distinct
    coalesce(t.headline_story, b.headline_story, ev.story_id) as story_id,
    case
        when t.headline_story is not null then 'headline'
        when b.headline_story is not null then 'headline_via_event'
        else 'event'
    end as grouped_by,
    t.event_id,
    t.article_url,
    t.outlet_domain,
    t.mentioned_at,
    t.copy_key,
    t.is_syndicated,
    coalesce(t.story_headline, b.story_headline) as story_headline
from tagged t
left join borrowed b on b.copy_key = t.copy_key
left join {{ ref('int_event_stories') }} ev on ev.event_id = t.event_id
where coalesce(t.headline_story, b.headline_story, ev.story_id) is not null
