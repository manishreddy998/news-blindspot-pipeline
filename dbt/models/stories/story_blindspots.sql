-- Coverage split by lean for each story, and a blindspot flag.
--
-- An article counts once per story even if it mentions several of its events,
-- and copies of one syndicated article count once per lean.
-- Center articles are counted and shown but the flag only compares left and
-- right, since a blindspot means one side is barely covering the story.
-- A story is flagged when it was grouped by headline, has at least
-- min_sided_articles left plus right articles, and one side has at least
-- blindspot_threshold of them.
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
),

-- Wilson score interval for the bigger side's share. With 4 articles a 4 to 0 split
-- is still uncertain, so the lower bound tells us how sure we can be.
wilson as (
    select
        *,
        greatest(left_share, 1 - left_share) as dominant_share,
        (
            greatest(left_share, 1 - left_share) + {{ var('wilson_z') }} * {{ var('wilson_z') }} / (2 * sided_articles)
            - {{ var('wilson_z') }} * sqrt(
                greatest(left_share, 1 - left_share) * (1 - greatest(left_share, 1 - left_share)) / sided_articles
                + {{ var('wilson_z') }} * {{ var('wilson_z') }} / (4 * sided_articles * sided_articles))
        ) / (1 + {{ var('wilson_z') }} * {{ var('wilson_z') }} / sided_articles) as dominant_share_low
    from shares
    where sided_articles > 0
    union all
    select *, cast(null as {{ 'float64' if target.type == 'bigquery' else 'double' }}),
           cast(null as {{ 'float64' if target.type == 'bigquery' else 'double' }})
    from shares
    where sided_articles = 0
),

flagged as (
    select
        w.*,
        st.grouped_by = 'headline'
            and w.sided_articles >= {{ var('min_sided_articles') }}
            and w.dominant_share >= {{ var('blindspot_threshold') }} as is_blindspot
    from wilson w
    join {{ ref('stories') }} st on st.story_id = w.story_id
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
    s.sided_articles,
    s.left_share,
    1 - s.left_share as right_share,
    -- 0 means an even split, 1 means only one side covered it.
    abs(2 * s.left_share - 1) as blindspot_score,
    s.dominant_share,
    s.dominant_share_low,
    s.is_blindspot,
    case when s.is_blindspot and s.left_share >= 0.5 then 'right'
         when s.is_blindspot then 'left' end as blindspot_for,
    -- strong: even the low end of the interval says one side has most of the coverage.
    case when s.is_blindspot and s.dominant_share_low >= 0.5 then 'strong'
         when s.is_blindspot then 'weak' end as confidence
from flagged s
join {{ ref('stories') }} st on st.story_id = s.story_id
