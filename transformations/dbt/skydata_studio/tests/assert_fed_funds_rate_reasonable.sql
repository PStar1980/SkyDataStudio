select *
from {{ ref('fct_fed_funds_rate_daily') }}
where rate < 0 or rate > 100
