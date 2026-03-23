# Security

## Access Control

- Follow least-privilege RBAC. Use database roles for object-level grants.
- Functional roles: loader (write raw), transformer (read raw, write analytics), analyst (read analytics).
- Use masking policies for PII columns and row access policies for multi-tenant isolation.

## Credentials

Never hardcode credentials.

BAD:
```python
session = Session.builder.configs({"password": "hunter2"}).create()
```

GOOD:
```python
session = Session.builder.configs({
    "account": os.environ["SNOWFLAKE_ACCOUNT"],
    "user": os.environ["SNOWFLAKE_USER"],
    "password": os.environ["SNOWFLAKE_PASSWORD"]
}).create()
```

## Data Sharing

- `CREATE SHARE` for zero-copy cross-account sharing.
- Snowflake Marketplace for data exchange.
- Secure views and secure UDFs for controlling shared data access.
