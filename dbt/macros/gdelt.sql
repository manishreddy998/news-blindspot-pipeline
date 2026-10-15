{# GDELT stores times as numbers like 20261015193000 (UTC). #}
{% macro parse_gdelt_ts(col) -%}
  {%- if target.type == 'bigquery' -%}
    parse_timestamp('%Y%m%d%H%M%S', cast({{ col }} as string))
  {%- else -%}
    strptime(cast({{ col }} as varchar), '%Y%m%d%H%M%S')
  {%- endif -%}
{%- endmacro %}

{% macro hash_key(expr) -%}
  {%- if target.type == 'bigquery' -%}
    to_hex(md5({{ expr }}))
  {%- else -%}
    md5({{ expr }})
  {%- endif -%}
{%- endmacro %}

{# BigQuery wants daily partitions on big tables, DuckDB ignores this. #}
{% macro day_partition(field) -%}
  {%- if target.type == 'bigquery' -%}
    {{ return({'field': field, 'data_type': 'timestamp', 'granularity': 'day'}) }}
  {%- else -%}
    {{ return(none) }}
  {%- endif -%}
{%- endmacro %}

{# First capture group of a regex. BigQuery returns the group by default. #}
{% macro regex_group(expr, pattern) -%}
  {%- if target.type == 'bigquery' -%}
    regexp_extract({{ expr }}, r'{{ pattern }}')
  {%- else -%}
    regexp_extract({{ expr }}, '{{ pattern }}', 1)
  {%- endif -%}
{%- endmacro %}
