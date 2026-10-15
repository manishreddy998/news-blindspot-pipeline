-- Coverage split by lean for each story, and a blindspot flag.
--
-- An article counts once per story even if it mentions several of its events.
-- Center articles are counted and shown but the flag only compares left and
-- right, since a blindspot means one side is barely covering the story.
with counts as (
    select
        story_id,
        count(*) as total_articles,
        sum(case when lean is not null then 1 else 0 end) as rated_articles,
        sum(case when lean = 'left' then 1 else 0 end) as left_articles,
        sum(case when lean = 'center' then 1 else 0 end) as center_articles,
        sum(case when lean = 'right' then 1 else 0 end) as right_articles
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
    st.actors,
    st.action_place,
    st.event_root_code,
    s.total_articles,
    s.rated_articles,
    s.left_articles,
    s.center_articles,
    s.right_articles,
    s.left_share,
    1 - s.left_share as right_share,
    -- 0 means an even split, 1 means only one side covered it.
    abs(2 * s.left_share - 1) as blindspot_score,
    s.rated_articles >= {{ var('min_rated_articles') }}
        and s.sided_articles > 0
        and greatest(s.left_share, 1 - s.left_share) >= {{ var('blindspot_threshold') }} as is_blindspot,
    case
        when s.left_share >= {{ var('blindspot_threshold') }} then 'right'
        when 1 - s.left_share >= {{ var('blindspot_threshold') }} then 'left'
    end as blindspot_for
from shares s
join {{ ref('stories') }} st on st.story_id = s.story_id
