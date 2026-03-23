# SQL Fundamentals

## Architecture

Snowflake separates storage (columnar micro-partitions), compute (elastic virtual warehouses), and services (metadata, security, optimization). Scale compute independently from storage.

## Naming Conventions

Use `snake_case` for all identifiers (tables, columns, schemas). Avoid double-quoted identifiers — they create case-sensitive names that require constant quoting.

BAD:
```sql
CREATE TABLE "UserData" ("UserID" INT, "Created At" TIMESTAMP);
```

GOOD:
```sql
CREATE TABLE user_data (user_id INT, created_at TIMESTAMP_NTZ);
```

## CTEs Over Nested Subqueries

Use `WITH` clauses for readable, maintainable SQL. Use `CREATE OR REPLACE` for idempotent DDL.

BAD:
```sql
SELECT * FROM (
    SELECT * FROM (
        SELECT user_id, SUM(amount) AS total FROM orders GROUP BY user_id
    ) WHERE total > 100
) WHERE user_id IN (SELECT user_id FROM active_users);
```

GOOD:
```sql
WITH order_totals AS (
    SELECT user_id, SUM(amount) AS total FROM orders GROUP BY user_id
),
high_value AS (
    SELECT user_id, total FROM order_totals WHERE total > 100
)
SELECT h.user_id, h.total
FROM high_value h
JOIN active_users a ON h.user_id = a.user_id;
```

## MERGE for Upserts

```sql
MERGE INTO target t USING source s ON t.id = s.id
WHEN MATCHED THEN UPDATE SET t.name = s.name, t.updated_at = CURRENT_TIMESTAMP()
WHEN NOT MATCHED THEN INSERT (id, name, updated_at) VALUES (s.id, s.name, CURRENT_TIMESTAMP());
```

## Stored Procedures — Colon Prefix

In SQL stored procedures (BEGIN...END blocks), variables and parameters must use colon `:` prefix inside SQL statements. Without the colon, Snowflake treats them as column identifiers and raises "invalid identifier" errors.

BAD:
```sql
CREATE PROCEDURE my_proc(p_id INT) RETURNS STRING LANGUAGE SQL AS
BEGIN
    LET result STRING;
    SELECT name INTO result FROM users WHERE id = p_id;
    RETURN result;
END;
```

GOOD:
```sql
CREATE PROCEDURE my_proc(p_id INT) RETURNS STRING LANGUAGE SQL AS
BEGIN
    LET result STRING;
    SELECT name INTO :result FROM users WHERE id = :p_id;
    RETURN result;
END;
```

## Semi-Structured Data

- Use VARIANT, OBJECT, and ARRAY types for JSON, Avro, Parquet, ORC.
- Access nested fields with colon notation: `src:customer.name::STRING`.
- Always cast extracted values explicitly: `src:price::NUMBER(10,2)`.
- Use LATERAL FLATTEN to unnest arrays:

```sql
SELECT f.value:name::STRING AS name
FROM my_table, LATERAL FLATTEN(input => src:items) f;
```

- Flatten semi-structured into relational columns when data contains dates, numbers as strings, or arrays — enables micro-partition pruning.
- VARIANT null vs SQL NULL: JSON `null` is stored as the string "null". Use `STRIP_NULL_VALUE = TRUE` on load.

## Time Travel and Data Protection

```sql
-- Point-in-time query
SELECT * FROM my_table AT(TIMESTAMP => '2024-01-15 10:00:00'::TIMESTAMP);
SELECT * FROM my_table BEFORE(STATEMENT => '<query_id>');

-- Undrop
UNDROP TABLE my_table;

-- Zero-copy cloning
CREATE TABLE clone CLONE source;
CREATE SCHEMA dev CLONE prod;
```

Time Travel retains 1 day by default, up to 90 on Enterprise+.

## Bulk Loading

```sql
COPY INTO raw_events FROM @my_stage
    FILE_FORMAT = (TYPE = 'JSON' STRIP_NULL_VALUE = TRUE)
    ON_ERROR = 'CONTINUE';
```

## Window Functions

```sql
SELECT user_id, event_timestamp,
    ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY event_timestamp) AS event_seq,
    LAG(event_timestamp) OVER (PARTITION BY user_id ORDER BY event_timestamp) AS prev_event
FROM events;
```

## Temporary and Transient Tables

```sql
-- Temporary: session-scoped, auto-dropped
CREATE TEMPORARY TABLE staging AS SELECT * FROM @stage;

-- Transient: persistent but no Fail-safe (lower storage cost)
CREATE TRANSIENT TABLE etl_staging (...);
```
