-- Shares and scores must stay between 0 and 1, and lean counts must add up.
-- A syndicated article carried by outlets of different leans counts once per lean,
-- so rated articles can pass unique articles, but never the number of URLs.
select story_id
from {{ ref('story_blindspots') }}
where left_share < 0 or left_share > 1
   or blindspot_score < 0 or blindspot_score > 1
   or left_articles + center_articles + right_articles != rated_articles
   or rated_articles > total_articles
   or unique_articles > total_articles
