# PatrickJS/awesome-cursorrules Format Spec

## Repository
- **GitHub**: PatrickJS/awesome-cursorrules
- **Stars**: ~13,000
- **Type**: Rules collection (.cursorrules files)

## File Structure
Directory per rule set: `rules/{slug}-cursorrules-prompt-file/.cursorrules` + `README.md`

Slug convention: `snowflake-{topic}-cursorrules-prompt-file`

We contributed 3 directories:
- `snowflake-data-engineering-cursorrules-prompt-file`
- `snowflake-cortex-ai-cursorrules-prompt-file`
- `snowflake-snowpark-dbt-cursorrules-prompt-file`

## Frontmatter
None. File opens directly with `//` comment lines.

## Section Convention
`// ═══` box-comment dividers with ALL-CAPS headings. Sub-items as `//` comment bullets. No numbered sections.

Example:
```
// ═══════════════════════════════════════════════════════════
//  SECTION TITLE
// ═══════════════════════════════════════════════════════════
```

## Code Examples
Bare SQL/Python inline (no fenced markdown code blocks). No BAD/GOOD pairs.

## Registry/Index
`README.md` at repo root — add a markdown bullet per entry with relative link + description.

## Metadata
`README.md` inside each rule directory: author, description, usage instructions.

## Canonical Domains to Include
Split into 3 topic files:
1. Data Engineering: sql-fundamentals + data-pipelines + performance
2. Cortex AI: cortex-ai (functions + search)
3. Snowpark + dbt: snowpark-python + dbt-snowflake

Each ~130-170 lines.

## Special Notes
- Uses `//` comment syntax throughout (not markdown)
- Anti-patterns from `anti-patterns.md` go as bullet lists at end of each file
- Security content distributed across files where relevant
- PR #200 already submitted
