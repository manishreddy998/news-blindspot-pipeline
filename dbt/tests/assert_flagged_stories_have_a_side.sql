-- A flagged story must say which side is missing it.
select story_id from {{ ref('story_blindspots') }}
where is_blindspot and blindspot_for is null
