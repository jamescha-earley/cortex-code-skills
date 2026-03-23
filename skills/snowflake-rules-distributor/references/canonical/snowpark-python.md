# Snowpark Python

## Session Setup

```python
from snowflake.snowpark import Session
import os

session = Session.builder.configs({
    "account": os.environ["SNOWFLAKE_ACCOUNT"],
    "user": os.environ["SNOWFLAKE_USER"],
    "password": os.environ["SNOWFLAKE_PASSWORD"],
    "role": "my_role",
    "warehouse": "my_wh",
    "database": "my_db",
    "schema": "my_schema"
}).create()
```

Never hardcode credentials. Use environment variables or Snowflake's secrets manager.

## DataFrame API

DataFrames are lazy — operations build a query plan, executed on `collect()`/`show()`.

```python
from snowflake.snowpark.functions import col, sum as sum_, when, lit

df = session.table("orders")
result = (
    df.filter(col("status") == "completed")
    .group_by("region")
    .agg(sum_("amount").alias("total_revenue"))
    .sort(col("total_revenue").desc())
)
result.show()  # Executes the query
```

## Scalar UDFs

```python
from snowflake.snowpark.functions import udf
from snowflake.snowpark.types import StringType

@udf(name="classify_tier", replace=True, return_type=StringType())
def classify_tier(amount: float) -> str:
    if amount > 10000: return "enterprise"
    elif amount > 1000: return "business"
    return "starter"
```

## Vectorized UDFs — Use for Batch/ML Workloads

10-100x faster than scalar UDFs. Required for ML inference.

BAD:
```python
# Scalar UDF for ML inference (slow — one row at a time)
@udf(name="predict")
def predict(val: float) -> float:
    import pickle
    model = pickle.load(open("model.pkl", "rb"))
    return float(model.predict([[val]])[0])
```

GOOD:
```python
# Vectorized UDF (10-100x faster — batch processing)
@udf(name="predict", packages=["scikit-learn", "pandas"])
def predict(vals: pd.Series) -> pd.Series:
    import pickle, sys
    model = pickle.load(open(sys.path[0] + "/model.pkl", "rb"))
    return pd.Series(model.predict(vals.values.reshape(-1, 1)))
```

## UDTFs (Table Functions)

```python
from snowflake.snowpark.functions import udtf
from snowflake.snowpark.types import StructType, StructField, StringType

class Tokenizer:
    def process(self, text: str):
        for token in text.split():
            yield (token,)
```

## Stored Procedures

```python
from snowflake.snowpark.functions import sproc

@sproc(name="daily_etl", replace=True, packages=["snowflake-snowpark-python"])
def daily_etl(session: Session) -> str:
    raw = session.table("raw_events")
    cleaned = raw.filter(raw["event_type"].is_not_null())
    cleaned.write.mode("overwrite").save_as_table("cleaned_events")
    return f"Processed {cleaned.count()} rows"
```
