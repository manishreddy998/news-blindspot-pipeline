-- One row per story and article, with the outlet's lean when we have one.
select distinct
    ev.story_id,
    m.article_url,
    m.outlet_domain,
    b.lean
from {{ ref('int_event_stories') }} ev
join {{ ref('stg_gdelt_mentions') }} m on m.event_id = ev.event_id
left join {{ ref('outlet_bias') }} b on b.domain = m.outlet_domain
