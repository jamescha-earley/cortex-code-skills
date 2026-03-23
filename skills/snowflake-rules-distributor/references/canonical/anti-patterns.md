# Anti-Patterns

Cross-cutting rules that apply across all Snowflake development.

## Cortex AI
- Do NOT use old function names (COMPLETE, CLASSIFY_TEXT, EXTRACT_ANSWER, etc.) — use AI_* versions.
- Do NOT use AI_COMPLETE for simple classification — use AI_CLASSIFY (purpose-built, cheaper).
- Do NOT pass entire tables through AI_COMPLETE row-by-row without checking cost via AI_COUNT_TOKENS first.
- Do NOT hardcode model names without considering regional availability.

## Data Pipelines
- Do NOT use Streams+Tasks for simple transformations that Dynamic Tables can handle.
- Do NOT set TARGET_LAG shorter than needed — directly impacts cost.
- Do NOT forget `ALTER TASK ... RESUME` after creation — tasks start suspended.

## Snowpark Python
- Do NOT use `collect()` on large DataFrames — process server-side.
- Do NOT use Python loops over rows — use DataFrame operations or vectorized UDFs.
- Do NOT use scalar UDFs for ML inference — use vectorized UDFs.

## dbt
- Do NOT use `{{ this }}` without `{% if is_incremental() %}` guard.
- Do NOT skip `dbt test` — data quality issues compound downstream.
- Do NOT use `table` materialization for large fact tables — use `incremental` or `dynamic_table`.

## SQL
- Do NOT use double-quoted identifiers unless absolutely necessary.
- Do NOT forget the colon prefix (`:variable`) in stored procedure SQL bodies.
- Do NOT set `cluster_by` on small tables (< 1TB) — Snowflake auto-clusters well.

## Common Error Patterns

### "Object does not exist"
- Check `USE DATABASE/SCHEMA` context or fully qualify names.
- Check role has grants: `SHOW GRANTS ON TABLE db.schema.table;`
- Quoted identifiers are case-sensitive.

### "Numeric value is not recognized"
- VARIANT data not cast properly. Fix: `src:field::NUMBER(10,2)`.

### Stored Procedure "Invalid identifier"
- Missing colon prefix. Fix: `:variable_name` not `variable_name`.

### "Cannot change column type"
- Snowflake does not support ALTER COLUMN type changes.
- Workaround: recreate table with new schema, COPY data.

### Task Not Running
- Check `ALTER TASK ... RESUME`.
- Check `WHEN` condition: `SYSTEM$STREAM_HAS_DATA()` returns false if stream is empty.
- Check warehouse availability and privileges.

### Dynamic Table Debugging

```sql
SELECT * FROM TABLE(INFORMATION_SCHEMA.DYNAMIC_TABLE_REFRESH_HISTORY(
    NAME => 'my_db.my_schema.my_dt'))
ORDER BY data_timestamp DESC LIMIT 10;
```

### Stream/Pipe Health

```sql
SELECT SYSTEM$STREAM_HAS_DATA('my_stream');
SELECT SYSTEM$PIPE_STATUS('my_pipe');
```
