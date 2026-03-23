# continuedev/awesome-rules Format Spec

## Repository
- **GitHub**: continuedev/awesome-rules
- **Stars**: ~500+
- **Type**: Rules collection with CLI distribution (rules-cli)
- **Special**: Has a `rules-cli` that renders rules to Cursor, Continue, Windsurf, Claude, Copilot, Codex, Cline, Cody, and Amp formats

## File Structure
Directory per rule: `rules/{technology-focus-description}/rule.md`

Directory naming: `{technology}-{focus}-{description}`
Example: `snowflake-data-engineering-best-practices`

## Frontmatter
YAML frontmatter — follows amplified.dev standard:

```yaml
---
description: Brief description
globs: "**/*.sql"
alwaysApply: false
---
```

`alwaysApply: true` means the rule is always active. `false` means it's only applied when matching files are open.

## Section Convention
Standard markdown `##` and `###`. No numbering. Content-first writing.

## Code Examples
Fenced markdown code blocks. No specific BAD/GOOD convention required but examples encouraged.

## Registry/Index
Update `README.md` at repo root — add entry to appropriate category section.

Also consider publishing via `rules-cli`:
```bash
rules login
rules publish
```

## Metadata
YAML frontmatter only: description, globs, alwaysApply.

## Canonical Domains to Include
Can do multiple rules (directories):
1. `snowflake-sql-best-practices` — sql-fundamentals + performance
2. `snowflake-data-pipelines` — data-pipelines
3. `snowflake-cortex-ai` — cortex-ai
4. `snowflake-snowpark-python` — snowpark-python
5. `snowflake-dbt-integration` — dbt-snowflake

Or single combined rule:
1. `snowflake-development-best-practices` — all canonical content

## Special Notes
- PR not yet submitted — this is a NEW target
- The `rules-cli` renders to 9 AI tool formats automatically
- Contributing guide: CONTRIBUTING.md in `.continue/rules`
- License: CC0 1.0 Universal
- inspired by amplified.dev standard
