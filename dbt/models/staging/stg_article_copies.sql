-- Group copies of the same article that were published on many sites.
--
-- Syndication networks (local radio sites on iheart.com, regional papers
-- sharing one newsroom) post the same story under many hostnames. Counting
-- each copy would let one newsroom swing a story's lean split. The last part
-- of the URL path (the slug) is nearly always the same across copies, so we
-- use it as the copy key when it's long enough to be specific.
with urls as (
    select distinct
        article_url,
        outlet_domain,
        lower({{ regex_group('article_url', '^[a-z]+://([^/]+)') }}) as host,
        lower({{ regex_group("rtrim(regexp_replace(article_url, '[?#].*', ''), '/')", '([^/]+)$') }}) as slug
    from {{ ref('stg_gdelt_mentions') }}
),

keyed as (
    select
        *,
        case when length(slug) >= 25 then slug else article_url end as copy_key
    from urls
)

select
    article_url,
    outlet_domain,
    host,
    copy_key,
    count(distinct host) over (partition by copy_key) as copy_hosts,
    count(distinct host) over (partition by copy_key) >= 3 as is_syndicated
from keyed
