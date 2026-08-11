{{ config(tags=['semantic_utility']) }}

select
    generated_date::date as date_day
from generate_series(
    date '1954-01-01',
    current_date + interval '366 days',
    interval '1 day'
) as generated_dates(generated_date)
