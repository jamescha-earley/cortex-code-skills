# Performance

## Cluster Keys

Define on columns used in WHERE, JOIN, or GROUP BY for very large tables (multi-TB). Range queries benefit most.

BAD:
```sql
-- Clustering a small table or on a high-cardinality random column
ALTER TABLE small_lookups CLUSTER BY (uuid_column);
```

GOOD:
```sql
-- Cluster large fact tables on commonly filtered columns
ALTER TABLE large_events CLUSTER BY (event_date, region);
```

Diagnostics:
```sql
SELECT SYSTEM$CLUSTERING_INFORMATION('my_table', '(event_date, region)');
-- Look for: average_overlaps (lower is better), average_depth (lower is better)
```

## Search Optimization Service

Enable for point-lookup queries on high-cardinality columns, substring/regex searches, and VARIANT field lookups.

```sql
ALTER TABLE logs ADD SEARCH OPTIMIZATION
    ON EQUALITY(sender_ip), SUBSTRING(error_message);
```

## Warehouse Sizing

- Size by query complexity, not data volume. Start X-Small, scale up.
- Separate warehouses per workload (ETL, analytics, data science, Cortex AI).
- `AUTO_SUSPEND = 60`, `AUTO_RESUME = TRUE` for cost control.
- Multi-cluster warehouses for concurrency scaling.

```sql
CREATE WAREHOUSE etl_wh WITH
    WAREHOUSE_SIZE = 'MEDIUM'
    AUTO_SUSPEND = 60
    AUTO_RESUME = TRUE;
```

## Avoid SELECT *

Snowflake uses columnar storage — scanning fewer columns is cheaper and faster.

BAD:
```sql
SELECT * FROM wide_events_table WHERE event_date = '2024-01-15';
```

GOOD:
```sql
SELECT event_id, event_type, user_id, event_timestamp
FROM wide_events_table
WHERE event_date = '2024-01-15';
```

## Query Performance Debugging

```sql
-- Find slow queries
SELECT query_id, query_text, execution_time, bytes_scanned,
    partitions_scanned, partitions_total
FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
WHERE execution_time > 60000
    AND start_time > DATEADD('day', -7, CURRENT_TIMESTAMP())
ORDER BY execution_time DESC LIMIT 20;
```

Key metrics:
- **Partitions scanned vs total**: low ratio = good pruning
- **Bytes spilled to local/remote**: warehouse too small
- **Compilation time**: simplify query or break into CTEs
- **Queue time**: increase warehouse size or use multi-cluster

## Cost Analysis

```sql
-- Credit usage by warehouse (last 30 days)
SELECT warehouse_name, SUM(credits_used) AS total_credits
FROM SNOWFLAKE.ACCOUNT_USAGE.WAREHOUSE_METERING_HISTORY
WHERE start_time > DATEADD('day', -30, CURRENT_TIMESTAMP())
GROUP BY warehouse_name ORDER BY total_credits DESC;
```

### Resource Monitors

```sql
CREATE RESOURCE MONITOR etl_monitor
    WITH CREDIT_QUOTA = 100
    TRIGGERS ON 75 PERCENT DO NOTIFY
             ON 90 PERCENT DO SUSPEND
             ON 100 PERCENT DO SUSPEND_IMMEDIATE;

ALTER WAREHOUSE etl_wh SET RESOURCE_MONITOR = etl_monitor;
```

### Token Cost Estimation (Cortex AI)

```sql
SELECT SUM(AI_COUNT_TOKENS('claude-4-sonnet', review_text)) AS total_tokens
FROM reviews;
```
