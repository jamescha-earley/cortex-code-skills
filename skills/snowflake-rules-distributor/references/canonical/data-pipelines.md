# Data Pipelines

## Choosing Your Approach

| Approach | When to Use |
|----------|-------------|
| Dynamic Tables | Declarative transformations. Define the query, Snowflake handles refresh. Best for most pipelines. |
| Streams + Tasks | Imperative CDC + scheduling. Best for procedural logic, stored procedure calls. |
| Snowpipe | Continuous file loading from S3/GCS/Azure. |
| Snowpipe Streaming | Low-latency row-level ingestion via SDK (Java, Python). |

**End-to-end pattern**: Snowpipe → Dynamic Table chain (simplest pipeline).

## Dynamic Tables

Declarative, auto-refreshing transformations. Chain them for multi-step pipelines.

```sql
CREATE OR REPLACE DYNAMIC TABLE cleaned_events
    TARGET_LAG = '5 minutes'
    WAREHOUSE = transform_wh
    AS
    SELECT event_id, event_type, user_id, event_timestamp
    FROM raw_events
    WHERE event_type IS NOT NULL;

-- Chain for multi-step pipelines
CREATE OR REPLACE DYNAMIC TABLE user_sessions
    TARGET_LAG = '10 minutes'
    WAREHOUSE = transform_wh
    AS
    SELECT user_id,
        MIN(event_timestamp) AS session_start,
        MAX(event_timestamp) AS session_end,
        COUNT(*) AS event_count
    FROM cleaned_events
    GROUP BY user_id;
```

- `TARGET_LAG`: freshness target. Shorter lag = higher cost.
- `REFRESH_MODE`: AUTO (default), FULL, or INCREMENTAL.
- Manage: `ALTER DYNAMIC TABLE ... SET TARGET_LAG / REFRESH / SUSPEND / RESUME`.

**Design tip**: Set TARGET_LAG progressively — tighter at the top (data freshness), looser at the bottom (cost efficiency).

## Streams and Tasks

Use when you need procedural logic, stored procedure calls, or imperative CDC.

```sql
CREATE OR REPLACE STREAM raw_events_stream ON TABLE raw_events;
-- APPEND_ONLY = TRUE for insert-only sources (lower overhead)

CREATE OR REPLACE TASK process_events
    WAREHOUSE = transform_wh
    SCHEDULE = 'USING CRON 0 */1 * * * America/Los_Angeles'
    WHEN SYSTEM$STREAM_HAS_DATA('raw_events_stream')
    AS
    INSERT INTO cleaned_events
    SELECT event_id, event_type, user_id, event_timestamp
    FROM raw_events_stream
    WHERE event_type IS NOT NULL;

-- Tasks start SUSPENDED — must resume
ALTER TASK process_events RESUME;
```

- Task DAGs: `CREATE TASK child_task ... AFTER parent_task ...`
- Stream columns: `METADATA$ACTION`, `METADATA$ISUPDATE`, `METADATA$ROW_ID`.

## Snowpipe

Continuous file loading from cloud storage.

```sql
CREATE OR REPLACE PIPE my_pipe AUTO_INGEST = TRUE AS
    COPY INTO raw_events FROM @my_external_stage
    FILE_FORMAT = (TYPE = 'JSON');
```

## Multi-Step Pipeline Design

1. Raw ingestion (Snowpipe or external tables)
2. Cleaning/validation (Dynamic Table, short lag)
3. Business logic/aggregation (Dynamic Table, moderate lag)
4. Consumption layer (Dynamic Table or materialized view)
