select
    observation_date::text as observation_key,
    observation_date,
    observation_month,
    observation_year,
    rate,
    previous_rate,
    rate_change,
    rate_change_bps,
    case
        when previous_rate is null then 'BASELINE'
        when rate > previous_rate then 'UP'
        when rate < previous_rate then 'DOWN'
        else 'UNCHANGED'
    end as rate_direction
from {{ ref('int_fed_funds_rate_changes') }}
