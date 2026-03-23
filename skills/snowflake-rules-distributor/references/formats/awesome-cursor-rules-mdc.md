# sanjeed5/awesome-cursor-rules-mdc Format Spec

## Repository
- **GitHub**: sanjeed5/awesome-cursor-rules-mdc
- **Stars**: ~3,400
- **Type**: Rules collection (.mdc files, flat directory)

## File Structure
Single file: `rules-mdc/{name}.mdc`

We contributed: `rules-mdc/snowflake.mdc` (518 lines)

## Frontmatter
YAML frontmatter with `description` and `globs`:

```yaml
---
description: Best practices for Snowflake SQL, data pipelines...
globs: **/*
---
```

## Section Convention
**Numbered hierarchically**: `## 1. Section Name`, `### 1.1. Subsection Name`

Example: `## 5. Cortex AI Functions` → `### 5.3. AI_CLASSIFY`

## Code Examples
Fenced code blocks with **BAD/GOOD pairs using emoji**:

```
❌ **BAD**:
\`\`\`sql
-- bad example
\`\`\`

✅ **GOOD**:
\`\`\`sql
-- good example
\`\`\`
```

This is the distinctive feature of this repo — every section should have at least one BAD/GOOD pair.

## Registry/Index
`rules.json` at repo root — add an object to the `libraries` array:

```json
{
  "name": "snowflake",
  "tags": ["database", "data-warehouse", "cloud", "sql", "analytics"]
}
```

Must be alphabetically sorted by name.

## Metadata
- `name` + `tags` in rules.json
- `description` + `globs` in frontmatter

## Canonical Domains to Include
ALL canonical files combined into ONE monolithic .mdc file:
1. Code Organization (sql-fundamentals)
2. Semi-Structured Data (sql-fundamentals)
3. Performance (performance)
4. Data Pipelines (data-pipelines)
5. Cortex AI Functions (cortex-ai)
6. Cortex Search (cortex-ai)
7. Snowpark Python (snowpark-python)
8. dbt on Snowflake (dbt-snowflake)
9. Security (security)
10. Common Pitfalls (anti-patterns)

Target: ~500 lines. Comparable to postgresql (360) and duckdb (393).

## Special Notes
- Single monolithic file — all content combined
- Must include BAD/GOOD examples (this is the repo's signature style)
- Sections numbered 1-10 with subsections 1.1, 1.2, etc.
- PR #30 already submitted
