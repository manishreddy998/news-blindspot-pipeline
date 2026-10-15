-- One row per story and article, with the outlet's lean when we have one.
-- copy_key lets the score count a syndicated article once, not once per site.
select distinct
    ev.story_id,
    m.article_url,
    m.outlet_domain,
    c.copy_key,
    c.is_syndicated,
    b.lean
from {{ ref('int_event_stories') }} ev
join {{ ref('stg_gdelt_mentions') }} m on m.event_id = ev.event_id
join {{ ref('stg_article_copies') }} c on c.article_url = m.article_url and c.outlet_domain = m.outlet_domain
left join {{ ref('outlet_bias') }} b on b.domain = m.outlet_domain
