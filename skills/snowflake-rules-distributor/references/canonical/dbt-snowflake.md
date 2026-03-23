# dbt on Snowflake

## Dynamic Table Materialization

```sql
{{ config(
    materialized='dynamic_table',
    snowflake_warehouse='transforming',
    target_lag='1 hour'
) }}

SELECT
    customer_id,
    SUM(amount) AS lifetime_value,
    MAX(order_date) AS last_order_date
FROM {{ ref('stg_orders') }}
GROUP BY 1
```

## Incremental Models

```sql
{{ config(materialized='incremental', unique_key='event_id') }}

SELECT event_id, event_type, user_id, event_timestamp
FROM {{ source('raw', 'events') }}
{% if is_incremental() %}
WHERE event_timestamp > (SELECT MAX(event_timestamp) FROM {{ this }})
{% endif %}
```

## Snowflake-Specific Configs

```sql
-- Transient tables (no Fail-safe, lower storage cost)
{{ config(materialized='table', transient=true) }}

-- Query tags for cost tracking
{{ config(query_tag='finance_team_daily') }}

-- Copy grants — preserve access when dbt replaces objects
{{ config(copy_grants=true) }}

-- Warehouse override per model
{{ config(snowflake_warehouse='large_wh') }}
```

## Project Structure

- Staging models (`stg_*`): rename, type-cast source columns
- Intermediate models: complex joins, business logic
- Mart models: final business-facing tables
- Use `dynamic_table` for streaming/near-real-time marts
- Use `incremental` for large fact tables
- Use `copy_grants=true` to avoid permission issues when dbt replaces objects
