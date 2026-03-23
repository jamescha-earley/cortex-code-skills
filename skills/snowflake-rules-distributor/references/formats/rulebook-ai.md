# botingw/rulebook-ai Format Spec

## Repository
- **GitHub**: botingw/rulebook-ai (main repo) + botingw/community-index (registry)
- **Stars**: ~580
- **Type**: Universal pack system generating rules for 10+ AI tools

## File Structure
Multi-file pack in a SEPARATE public repo. Structure:

```
{pack-name}/
├── manifest.yaml       (required)
├── README.md           (required)
└── rules/              (required)
    ├── 01-rules/       (always applied)
    │   ├── 01-topic.md
    │   ├── 02-topic.md
    │   └── 03-topic.md
    ├── 02-rules-architect/  (planning mode)
    │   └── 01-topic.md
    ├── 03-rules-code/       (implementation mode)
    │   └── 01-topic.md
    └── 04-rules-debug/      (debugging mode)
        └── 01-topic.md
```

Max 5 items at pack root (manifest.yaml, README.md, rules/).

We contributed: `jamescha-earley/snowflake-rulebook-pack` (8 files, 702 lines)

## Frontmatter
None on rule files. `manifest.yaml` at pack root:

```yaml
name: snowflake
version: 0.1.0
summary: Snowflake development best practices covering SQL, data pipelines, Cortex AI, Snowpark Python, and dbt.
```

## Section Convention
Unnumbered `##` and `###`. Directory numbering maps to modes:
- `01-rules` = always-on general rules
- `02-rules-architect` = planning/architecture mode
- `03-rules-code` = implementation mode
- `04-rules-debug` = debugging mode

## Code Examples
Fenced code blocks. Decision tables. No BAD/GOOD pairs.

## Registry/Index
TWO indexes to update:
1. `manifest.yaml` in the pack repo (created with the pack)
2. `packs.json` in `botingw/community-index` repo — add entry:

```json
{
  "name": "snowflake",
  "username": "jamescha-earley",
  "repo": "snowflake-rulebook-pack",
  "path": "snowflake",
  "description": "Snowflake development best practices..."
}
```

## Canonical Domains to Include
Split by MODE:
- **01-rules** (always): sql-fundamentals, data-pipelines, cortex-ai
- **02-rules-architect**: architecture decisions from data-pipelines + performance + dbt-snowflake
- **03-rules-code**: snowpark-python + dbt-snowflake + sql implementation patterns
- **04-rules-debug**: performance debugging + anti-patterns + error patterns

## Special Notes
- Requires creating a SEPARATE public repo for the pack
- PR goes to community-index, not the main rulebook-ai repo
- One pack install = rules generated for 10 AI tools (Cursor, Windsurf, Cline, RooCode, KiloCode, Warp, GitHub Copilot, Claude Code, Codex CLI, Gemini CLI)
- PR #2 already submitted to community-index
