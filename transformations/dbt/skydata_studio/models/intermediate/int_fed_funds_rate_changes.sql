with staged as (
    select *
    from {{ ref('stg_fed_funds_rate') }}
),
lagged as (
    select
        observation_date,
        rate,
        lag(rate) over (order by observation_date) as previous_rate
    from staged
)
select
    observation_date,
    date_trunc('month', observation_date)::date as observation_month,
    extract(year from observation_date)::integer as observation_year,
    rate,
    previous_rate,
    (rate - previous_rate)::numeric(10, 4) as rate_change,
    ((rate - previous_rate) * 100)::numeric(12, 2) as rate_change_bps
from lagged
