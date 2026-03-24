# Security

## Access Control

- Follow least-privilege RBAC. Use database roles for object-level grants.
- Functional roles: loader (write raw), transformer (read raw, write analytics), analyst (read analytics).
- Use masking policies for PII columns and row access policies for multi-tenant isolation.
- Audit ACCOUNTADMIN grants regularly — minimize direct usage.

```sql
-- Check who has ACCOUNTADMIN
SHOW GRANTS OF ROLE ACCOUNTADMIN;

-- Grant a functional role
GRANT ROLE transformer TO ROLE etl_service_role;
GRANT USAGE ON WAREHOUSE transform_wh TO ROLE transformer;
GRANT USAGE ON DATABASE analytics TO ROLE transformer;
```

## Network Policies

Control network access with hybrid policies (custom rules + Snowflake-managed SaaS rules for dbt, Tableau, Power BI, etc.).

```sql
-- Create network rule first
CREATE NETWORK RULE corp_network TYPE = IPV4 MODE = INGRESS
    VALUE_LIST = ('203.0.113.0/24', '198.51.100.0/24');

-- Create policy referencing rule (rules MUST exist before policy)
CREATE NETWORK POLICY corp_only
    ALLOWED_NETWORK_RULE_LIST = ('corp_network');

-- Apply to account or user
ALTER ACCOUNT SET NETWORK_POLICY = corp_only;
ALTER USER service_user SET NETWORK_POLICY = corp_only;
```

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

## Security Monitoring

```sql
-- Brute force detection (>5 failed logins from one IP in 1 hour)
SELECT client_ip, COUNT(*) AS failures
FROM SNOWFLAKE.ACCOUNT_USAGE.LOGIN_HISTORY
WHERE is_success = 'NO'
    AND event_timestamp > DATEADD('hour', -1, CURRENT_TIMESTAMP())
GROUP BY client_ip HAVING COUNT(*) > 5;

-- Large data exports (potential exfiltration)
SELECT user_name, query_text, rows_produced, bytes_scanned
FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
WHERE rows_produced > 1000000
    AND query_type IN ('SELECT', 'UNLOAD')
    AND start_time > DATEADD('day', -1, CURRENT_TIMESTAMP())
ORDER BY rows_produced DESC;

-- New privileged role grants
SELECT * FROM SNOWFLAKE.ACCOUNT_USAGE.GRANTS_TO_ROLES
WHERE granted_on = 'ROLE' AND privilege = 'USAGE'
    AND grantee_name IN ('ACCOUNTADMIN', 'SECURITYADMIN', 'SYSADMIN')
    AND created_on > DATEADD('day', -7, CURRENT_TIMESTAMP());
```

## Data Sharing

- `CREATE SHARE` for zero-copy cross-account sharing.
- Snowflake Marketplace for data exchange.
- Secure views and secure UDFs for controlling shared data access.
