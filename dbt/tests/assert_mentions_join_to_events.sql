{{ config(severity='warn', warn_if='>0') }}
-- Most mentions should point at an event we loaded. Mentions of events older
-- than the load window are normal, so this only warns below 80%.
with j as (
    select avg(case when e.event_id is not null then 1.0 else 0.0 end) as joined_share
    from {{ ref('stg_gdelt_mentions') }} m
    left join {{ ref('stg_gdelt_events') }} e on e.event_id = m.event_id
)
select joined_share from j where joined_share < 0.8
