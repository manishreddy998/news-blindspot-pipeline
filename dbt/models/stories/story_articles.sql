-- One row per story and article, with the outlet's lean when we have one.
-- copy_key lets the score count a syndicated article once, not once per site.
select distinct
    s.story_id,
    s.article_url,
    s.outlet_domain,
    s.copy_key,
    s.is_syndicated,
    b.lean
from {{ ref('int_article_stories') }} s
left join {{ ref('outlet_bias') }} b on b.domain = s.outlet_domain
