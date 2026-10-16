-- Every flag must meet the rule, and the interval must sit below the share.
select story_id from {{ ref('story_blindspots') }}
where (is_blindspot and (sided_articles < {{ var('min_sided_articles') }}
                         or dominant_share < {{ var('blindspot_threshold') }}
                         or grouped_by != 'headline'))
   or dominant_share_low > dominant_share + 0.000001
   or dominant_share_low < 0
