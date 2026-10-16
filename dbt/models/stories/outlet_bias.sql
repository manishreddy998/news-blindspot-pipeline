-- Outlet lean from the partisan audience scores (Robertson et al. 2018, CC0 1.0).
-- Score <= lean_left_max is left, >= lean_right_min is right, anything between is center.
select
    domain,
    partisan_score,
    case
        when partisan_score <= {{ var('lean_left_max') }} then 'left'
        when partisan_score >= {{ var('lean_right_min') }} then 'right'
        else 'center'
    end as lean,
    'Robertson et al. 2018, doi:10.7910/DVN/QAN5VX' as rating_source,
    'CC0-1.0' as rating_license
from {{ ref('partisan_audience_scores') }}
