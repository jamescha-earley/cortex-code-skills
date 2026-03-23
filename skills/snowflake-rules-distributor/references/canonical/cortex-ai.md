# Cortex AI

## Cortex AI Functions

Use these names — they are the current versions:

| Function | Purpose |
|----------|---------|
| `AI_COMPLETE` | General-purpose LLM completion (text, images, documents) |
| `AI_CLASSIFY` | Classify text/images into user-defined categories |
| `AI_FILTER` | Returns TRUE/FALSE for text/image input |
| `AI_AGG` | Aggregate insights across rows of text |
| `AI_EMBED` | Generate embedding vectors |
| `AI_EXTRACT` | Extract structured info from text/images/documents |
| `AI_SENTIMENT` | Sentiment score (-1 to 1) |
| `AI_SUMMARIZE_AGG` | Summarize across rows |
| `AI_SIMILARITY` | Embedding similarity between two inputs |
| `AI_TRANSCRIBE` | Transcribe audio/video from stages |
| `AI_PARSE_DOCUMENT` | OCR or text+layout extraction from documents |
| `AI_REDACT` | Redact PII from text |
| `AI_TRANSLATE` | Translate between languages |

Helper functions: `TO_FILE('@stage', 'filename')`, `AI_COUNT_TOKENS(model, text)`, `PROMPT('template {0}', arg)`, `TRY_COMPLETE`.

## AI_COMPLETE

Available models: claude-4-opus, claude-4-sonnet, claude-sonnet-4-5, claude-opus-4-5, claude-haiku-4-5, gemini-3-pro, llama3.1-70b, llama3.1-8b, llama3.3-70b, mistral-large2, mistral-small2, deepseek-r1.

```sql
-- Text completion
SELECT AI_COMPLETE(MODEL => 'claude-4-sonnet',
    PROMPT => 'Summarize: ' || review_text) AS summary
FROM reviews;

-- Document processing
SELECT AI_COMPLETE(MODEL => 'claude-4-sonnet',
    PROMPT => PROMPT('Extract the invoice total from {0}',
        TO_FILE('@docs', 'invoice.pdf')));

-- Structured JSON output
SELECT AI_COMPLETE(MODEL => 'claude-4-sonnet',
    PROMPT => 'Extract name, email, company as JSON: ' || raw_text
)::VARIANT AS extracted FROM contacts;
```

## AI_CLASSIFY

Use AI_CLASSIFY for classification instead of AI_COMPLETE — purpose-built and cheaper.

BAD:
```sql
SELECT AI_COMPLETE('claude-4-sonnet',
    'Classify into billing/technical/account/other: ' || ticket_text) FROM tickets;
```

GOOD:
```sql
-- Single-label
SELECT AI_CLASSIFY(ticket_text,
    ['billing', 'technical', 'account', 'other']) AS category
FROM tickets;

-- Multi-label classification
SELECT AI_CLASSIFY(input, categories, {'output_mode': 'multi'});
```

## Other Key Functions

```sql
-- AI_FILTER (natural-language WHERE)
SELECT * FROM reviews WHERE AI_FILTER(review_text, 'mentions product quality issues');

-- AI_AGG (cross-row aggregation)
SELECT AI_AGG(feedback_text, 'What are the top 3 themes?') FROM customer_feedback;

-- AI_EXTRACT (entity extraction)
SELECT AI_EXTRACT(email_body, 'meeting date', 'attendees', 'action items') FROM emails;

-- AI_SENTIMENT
SELECT review_text, AI_SENTIMENT(review_text) AS sentiment FROM product_reviews;

-- AI_PARSE_DOCUMENT (OCR)
SELECT AI_PARSE_DOCUMENT(TO_FILE('@docs', 'contract.pdf'), MODE => 'LAYOUT');

-- AI_REDACT (PII removal)
SELECT AI_REDACT(customer_notes) AS redacted FROM support_cases;
```

## Cortex Search — Hybrid Vector + Keyword Search

Managed search for RAG applications.

```sql
-- Single-index
CREATE OR REPLACE CORTEX SEARCH SERVICE my_search
    ON transcript_text
    ATTRIBUTES region, agent_id
    WAREHOUSE = my_wh
    TARGET_LAG = '1 day'
    EMBEDDING_MODEL = 'snowflake-arctic-embed-l-v2.0'
    AS (SELECT transcript_text, region, agent_id FROM support_transcripts);

-- Multi-index
CREATE OR REPLACE CORTEX SEARCH SERVICE my_multi_search
    TEXT INDEXES transcript_text, summary
    VECTOR INDEXES transcript_text (model='snowflake-arctic-embed-l-v2.0')
    ATTRIBUTES region
    WAREHOUSE = my_wh
    TARGET_LAG = '1 hour'
    AS (SELECT transcript_text, summary, region FROM support_transcripts);
```

### Querying — Python API

```python
from snowflake.core import Root

root = Root(session)
service = root.databases["db"].schemas["schema"].cortex_search_services["my_search"]
resp = service.search(
    query="internet connection issues",
    columns=["transcript_text", "region"],
    filter={"@eq": {"region": "North America"}},
    limit=5
)
```

Filter syntax: `{"@eq": {...}}`, `{"@contains": {...}}`, `{"@gte": {...}}`, `{"@and": [...]}`, `{"@or": [...]}`, `{"@not": ...}`.

### RAG Pattern

Search for context, pass to AI_COMPLETE:

```python
results = service.search(query=question, columns=["content"], limit=5)
context = "\n".join([r["content"] for r in results.results])
```

```sql
SELECT AI_COMPLETE(MODEL => 'claude-4-sonnet',
    PROMPT => 'Answer from context: ' || :context || ' Question: ' || :question);
```

## Privileges

Users need `USE AI FUNCTIONS` account privilege AND the `SNOWFLAKE.CORTEX_USER` database role. Both granted to PUBLIC by default.
