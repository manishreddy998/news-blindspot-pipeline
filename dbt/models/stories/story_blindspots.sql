-- Coverage split by lean for each story, and a blindspot flag.
--
-- An article counts once per story even if it mentions several of its events,
-- and copies of one syndicated article count once per lean.
-- Center articles are counted and shown but the flag only compares left and
-- right, since a blindspot means one side is barely covering the story.
with counts as (
    select
        story_id,
        count(distinct article_url) as total_articles,
        count(distinct copy_key) as unique_articles,
        count(distinct case when lean is not null then lean || copy_key end) as rated_articles,
        count(distinct case when lean = 'left' then copy_key end) as left_articles,
        count(distinct case when lean = 'center' then copy_key end) as center_articles,
        count(distinct case when lean = 'right' then copy_key end) as right_articles
    from {{ ref('story_articles') }}
    group by 1
),

shares as (
    select
        *,
        left_articles + right_articles as sided_articles,
        case when left_articles + right_articles > 0
             then cast(left_articles as {{ 'float64' if target.type == 'bigquery' else 'double' }}) / (left_articles + right_articles) end as left_share
    from counts
)

select
    s.story_id,
    st.story_day,
    st.headline,
    st.grouped_by,
    st.actors,
    st.action_place,
    st.event_root_code,
    s.total_articles,
    s.unique_articles,
    s.rated_articles,
    s.left_articles,
    s.center_articles,
    s.right_articles,
    s.left_share,
    1 - s.left_share as right_share,
    -- 0 means an even split, 1 means only one side covered it.
    abs(2 * s.left_share - 1) as blindspot_score,
    st.grouped_by = 'headline'
        and s.rated_articles >= {{ var('min_rated_articles') }}
        and s.sided_articles > 0
        and greatest(s.left_share, 1 - s.left_share) >= {{ var('blindspot_threshold') }} as is_blindspot,
    case
        when s.left_share >= {{ var('blindspot_threshold') }} then 'right'
        when 1 - s.left_share >= {{ var('blindspot_threshold') }} then 'left'
    end as blindspot_for
from shares s
join {{ ref('stories') }} st on st.story_id = s.story_id
