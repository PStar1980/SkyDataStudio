select
    observation_date::date as observation_date,
    rate::numeric(10, 4) as rate
from {{ source('studio_curated', 'fed_funds_rate') }}
