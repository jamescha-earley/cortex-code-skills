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

Deprecated names (do NOT use): `COMPLETE`, `CLASSIFY_TEXT`, `EXTRACT_ANSWER`, `PARSE_DOCUMENT`, `SUMMARIZE`, `TRANSLATE`, `SENTIMENT`, `EMBED_TEXT_768`.

Helper functions: `TO_FILE('@stage', 'filename')`, `AI_COUNT_TOKENS(model, text)`, `PROMPT('template {0}', arg)`, `TRY_COMPLETE`.

### TO_FILE Rules (Common Error Source)

Stage path and filename are SEPARATE arguments:

BAD:
```sql
TO_FILE('@db.schema.mystage/invoice.pdf')  -- concatenated path
```

GOOD:
```sql
TO_FILE('@db.schema.mystage', 'invoice.pdf')  -- separate arguments
```

When using `DIRECTORY()` output, the `relative_path` may include folder prefixes. Strip them with `SPLIT_PART(relative_path, '/', -1)`.

DDL commands (ALTER STAGE, CREATE STAGE) do NOT use the `@` prefix — only queries use `@`.

## AI_COMPLETE

### Pricing

| Token Type | Credits per Million |
|------------|-------------------|
| Input | 1.50 |
| Output | 7.50 |

Cost formula: `(input_tokens × 1.50 + output_tokens × 7.50) / 1,000,000`. Rule of thumb: ~4 characters ≈ 1 token.

### Models

Vision-capable: claude-4-opus, claude-4-sonnet, claude-3-7-sonnet, claude-3-5-sonnet, llama4-maverick, llama4-scout, openai-o4-mini, openai-gpt-4.1, pixtral-large.

Text-only: claude-sonnet-4-5, claude-opus-4-5, claude-haiku-4-5, gemini-3-pro, llama3.1-70b, llama3.1-8b, llama3.3-70b, mistral-large2, mistral-small2, deepseek-r1.

### Options

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `max_tokens` | INT | 4096 | Maximum tokens in response |
| `temperature` | FLOAT | 0.0 | Randomness (0.0 = deterministic) |
| `top_p` | FLOAT | 1.0 | Nucleus sampling threshold |
| `response_format` | OBJECT | - | Structured JSON output schema |
| `guardrails` | BOOLEAN | true | Content safety filters |

### Usage Patterns

```sql
-- Text completion
SELECT AI_COMPLETE('claude-4-sonnet',
    'Summarize: ' || review_text) AS summary
FROM reviews;

-- Vision / image analysis
SELECT AI_COMPLETE('claude-4-sonnet',
    'Analyze this chart and extract all data points.',
    TO_FILE('@db.schema.stage', 'chart.png')) AS analysis;

-- Document processing via PROMPT helper
SELECT AI_COMPLETE('claude-4-sonnet',
    PROMPT('Extract the invoice total from {0}',
        TO_FILE('@docs', 'invoice.pdf')));

-- Structured JSON output with schema
SELECT AI_COMPLETE('claude-4-sonnet',
    'Extract name, email, company from: ' || raw_text,
    {'response_format': {'type': 'json', 'schema': {
        'type': 'object',
        'properties': {
            'name': {'type': 'string'},
            'email': {'type': 'string'},
            'company': {'type': 'string'}
        },
        'required': ['name', 'email']
    }}}) AS extracted FROM contacts;

-- Multi-image comparison (conversation format)
SELECT AI_COMPLETE('claude-4-sonnet',
    [{'role': 'user', 'content': [
        {'type': 'text', 'text': 'Compare these two charts.'},
        {'type': 'image_url', 'image_url': {'url': TO_FILE('@stage', 'chart1.png')}},
        {'type': 'image_url', 'image_url': {'url': TO_FILE('@stage', 'chart2.png')}}
    ]}],
    {'max_tokens': 4096}) AS comparison;

-- Batch image analysis from stage
SELECT relative_path, AI_COMPLETE('claude-4-sonnet',
    'Extract all data from this chart.',
    TO_FILE('@db.schema.stage', relative_path)) AS analysis
FROM DIRECTORY(@db.schema.stage)
WHERE relative_path ILIKE '%.png' OR relative_path ILIKE '%.jpg';
```

## AI_CLASSIFY

Use AI_CLASSIFY for classification instead of AI_COMPLETE — purpose-built and cheaper. Up to 500 labels (>20 may reduce accuracy). Supports images via `TO_FILE()`.

BAD:
```sql
SELECT AI_COMPLETE('claude-4-sonnet',
    'Classify into billing/technical/account/other: ' || ticket_text) FROM tickets;
```

GOOD:
```sql
-- Single-label (access result with :labels[0]::VARCHAR)
SELECT AI_CLASSIFY(ticket_text,
    ['billing', 'technical', 'account', 'other']):labels[0]::VARCHAR AS category
FROM tickets;

-- Multi-label classification
SELECT AI_CLASSIFY(article_text,
    ['technology', 'finance', 'healthcare'],
    {'output_mode': 'multi'}):labels AS tags
FROM articles;

-- With category descriptions and few-shot examples
SELECT AI_CLASSIFY(text,
    [{'label': 'travel', 'description': 'content about traveling'},
     {'label': 'cooking', 'description': 'content about preparing food'}],
    {'task_description': 'Determine topics in the text',
     'output_mode': 'multi',
     'examples': [{'input': 'I love traveling with a good book',
                   'labels': ['travel'], 'explanation': 'mentions traveling'}]
    }):labels AS topics
FROM posts;

-- Image classification
SELECT AI_CLASSIFY(TO_FILE(file_url),
    ['electronics', 'clothing', 'furniture'],
    {'model': 'pixtral-large'}):labels[0]::VARCHAR AS category
FROM product_images;
```

## Other Key Functions

```sql
-- AI_FILTER (natural-language WHERE clause, returns BOOLEAN)
-- Performance tip: ALTER SESSION SET ENABLE_MODEL_CASCADES = true for 2-10x speedup
SELECT * FROM reviews WHERE AI_FILTER(review_text, 'mentions product quality issues');

-- AI_FILTER for semantic JOINs (fuzzy matching)
SELECT a.*, b.* FROM table_a a JOIN table_b b
    ON AI_FILTER(a.description, CONCAT('matches: ', b.description));

-- AI_AGG (cross-row aggregation, no context window limits — automatic chunking)
SELECT AI_AGG(feedback_text, 'What are the top 3 themes?') FROM customer_feedback;

-- AI_EXTRACT (structured field extraction, uses arctic_extract model — 5 credits/M tokens)
-- Max 100MB, 125 pages. TO_FILE rules apply (separate stage and filename args)
SELECT AI_EXTRACT(
    file => TO_FILE('@db.schema.docs', 'invoice.pdf'),
    responseFormat => ['invoice_number', 'total', 'vendor_name']
):response AS result;

-- AI_SENTIMENT
SELECT review_text, AI_SENTIMENT(review_text) AS sentiment FROM product_reviews;

-- AI_PARSE_DOCUMENT (OCR: 0.5 credits/1K pages, LAYOUT: 3.33 credits/1K pages)
-- Max 50MB, 500 pages. Supports page_split, page_filter, extract_images
SELECT AI_PARSE_DOCUMENT(TO_FILE('@docs', 'contract.pdf'), {'mode': 'LAYOUT'});

-- Chain: parse document then analyze with AI_COMPLETE
WITH parsed AS (
    SELECT AI_PARSE_DOCUMENT(
        TO_FILE('@stage', 'report.pdf'), {'mode': 'LAYOUT'}
    ):content::STRING AS text
)
SELECT AI_COMPLETE('claude-4-sonnet',
    'Extract key insights:\n\n' || text) AS insights
FROM parsed;

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
