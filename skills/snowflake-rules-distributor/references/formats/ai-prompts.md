# instructa/ai-prompts Format Spec

## Repository
- **GitHub**: instructa/ai-prompts
- **Stars**: ~700
- **Type**: Prompt/rules collection (.mdc files with JSON manifests)

## File Structure
Directory per topic: `prompts/{slug}/rule-{slug}.mdc` + `aiprompt.json`

We contributed 4 directories:
- `prompts/snowflake-sql/`
- `prompts/snowflake-cortex/`
- `prompts/snowflake-python/`
- `prompts/snowflake-dbt/`

## Frontmatter
YAML frontmatter with `description` and `globs`:

```yaml
---
description: Brief description of what the rules cover
globs: "**/*.sql, **/*.py"
---
```

## Section Convention
Unnumbered `##` H2 headers and `###` H3 for sub-topics. No numbering.

## Code Examples
Fenced markdown code blocks (` ```sql `, ` ```python `). No BAD/GOOD pairs.

## Registry/Index
`aiprompt.json` per directory with rich schema:

```json
{
  "name": "Snowflake SQL & Data Pipelines",
  "description": "...",
  "type": "prompt",
  "slug": "snowflake-sql",
  "development_process": ["data-engineering", "analytics"],
  "dev_categories": ["database", "data-warehouse"],
  "tags": ["snowflake", "sql", "data-warehouse", ...],
  "techStack": ["snowflake", "sql"],
  "ai_editor": ["cursor"],
  "author": { "name": "Snowflake DevRel", "url": "https://github.com/Snowflake-Labs" },
  "model": "claude-4-sonnet",
  "version": "1.0.0",
  "files": ["rule-snowflake-sql.mdc"],
  "published": true
}
```

## Metadata
All in `aiprompt.json`. Tags and techStack arrays.

## Canonical Domains to Include
Split into 4 topic files:
1. SQL & Pipelines: sql-fundamentals + data-pipelines
2. Cortex & Search: cortex-ai
3. Python: snowpark-python
4. dbt: dbt-snowflake

Each ~125-165 lines.

## Special Notes
- Anti-patterns inline within relevant sections
- Performance and security distributed across files
- PR #15 already submitted
