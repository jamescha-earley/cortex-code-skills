---
name: snowflake-rules-distributor
description: "Distribute Snowflake AI coding rules to open-source rule repositories. Maintains canonical Snowflake knowledge and adapts it to each repo's format. Use when: user wants to contribute Snowflake rules to a new repo, update existing contributions, check PR status, add a new format spec, or update canonical content. Triggers: snowflake rules, distribute rules, contribute rules, rules PR, cursor rules, agent rules, coding rules, update canonical, PR status, new repo contribution."
---

# Snowflake Rules Distributor

Maintain a single source of truth for Snowflake AI coding rules and distribute them across open-source rule repositories. Each repo has a different format — this skill handles the adaptation.

## Architecture

```
references/
├── canonical/          ← Single source of truth (Snowflake knowledge)
│   ├── sql-fundamentals.md
│   ├── data-pipelines.md
│   ├── cortex-ai.md
│   ├── snowpark-python.md
│   ├── dbt-snowflake.md
│   ├── performance.md
│   ├── security.md
│   └── anti-patterns.md
├── formats/            ← How each target repo wants content structured
│   ├── awesome-cursorrules.md
│   ├── ai-prompts.md
│   ├── awesome-cursor-rules-mdc.md
│   ├── rulebook-ai.md
│   ├── awesome-list.md
│   └── (add more as we target new repos)
└── pr-tracker.md       ← Living status of all PRs
```

**Key principle**: When canonical content changes, ALL future contributions use the updated version. Existing PRs may need updating too.

## Grounding

All canonical content MUST be grounded in official Snowflake documentation. Before writing or updating any canonical file:

1. Use `cortex search docs "<topic>"` to verify facts against current Snowflake docs
2. Cross-reference with Cortex Code's built-in Snowflake skills (cortex-ai-functions, dynamic-tables, snowpark-python, dbt-projects-on-snowflake, semantic-view, etc.) — these are authoritative
3. Never rely on training data alone for function names, syntax, or feature availability

## Workflow

### Step 1: Show Status

**Read** `references/pr-tracker.md` from this skill's directory.

For each PR listed, check current status:

```bash
gh pr view <PR_NUMBER> --repo <OWNER/REPO> --json state,mergedAt,reviews
```

Display a summary table:

```
| # | Repo | PR | Status | Date |
|---|------|----|--------|------|
```

### Step 2: Choose Action

Ask the user what they want to do:

1. **Contribute to a new repo** — Target a repo we haven't contributed to yet
2. **Update canonical content** — Edit a knowledge domain (e.g., new AI function added)
3. **Update an existing contribution** — Re-adapt canonical content for a repo after canonical changes
4. **Add a new format spec** — Document a new repo's conventions for future use
5. **Check PR status only** — Just run Step 1 and stop

### Step 3: Adapt Content (for "Contribute to new repo" or "Update existing")

#### 3a. Load format spec

**Read** the relevant format spec from `references/formats/<repo-name>.md`.

If no format spec exists for this repo:
- Clone the repo to `/tmp/`
- Analyze 2-3 existing entries to understand the format
- **Write** a new format spec to `references/formats/<repo-name>.md`
- Present to user for confirmation before proceeding

#### 3b. Load canonical content

**Read** the canonical files needed. Not every repo needs all domains — the format spec says which to include and how to split/combine them.

#### 3c. Generate adapted files

Transform canonical content following the format spec:
- Apply the correct file structure (single file vs multi-file vs directory)
- Apply frontmatter/metadata format
- Apply code example conventions (fenced vs bare, BAD/GOOD vs plain)
- Apply section numbering convention
- Apply registry/index updates needed
- Apply any repo-specific conventions (tags, globs, modes, etc.)

#### 3d. Git workflow

```bash
# Clone and branch
cd /tmp && gh repo fork <OWNER/REPO> --clone=true
cd /tmp/<REPO> && git remote set-url origin https://github.com/jamescha-earley/<REPO>.git
git checkout -b add-snowflake-rules

# ... create/write files ...

# Commit
git add -A
git commit -m "<message>

.... Generated with Cortex Code (https://docs.snowflake.com/en/user-guide/cortex-code/cortex-code)

Co-Authored-By: Cortex Code <noreply@snowflake.com>"
```

Present the diff to the user for review before pushing.

### Step 4: Submit PR

After user approves the diff:

```bash
# SSH workaround
git config --global --unset url."ssh://git@github.com/".insteadOf 2>/dev/null

# Push
git push -u origin add-snowflake-rules

# Restore SSH
git config --global url."ssh://git@github.com/".insteadOf "https://github.com/"

# Create PR
gh pr create --repo <OWNER/REPO> --title "<title>" --body "<structured body>"
```

Then **update** `references/pr-tracker.md` with the new PR entry.

### Step 5: Log Session (optional)

Offer to log via the `log-session` skill:
- WORK_TYPE: `content`
- TAGS: `rules, <repo-name>, open-source`
- ARTIFACTS: PR URL

## Stopping Points

- After Step 1: If user chose "Check PR status only"
- After Step 3d: Present diff for user review before pushing
- After Step 5: Session complete

## Format Spec Template

When adding a new format spec (`references/formats/<name>.md`), document:

```markdown
# <Repo Name> Format Spec

## Repository
- **GitHub**: owner/repo
- **Stars**: N
- **Type**: (rules collection | awesome list | pack system | CLI registry)

## File Structure
(single file | directory per entry | pack with subdirs)

## Frontmatter
(none | YAML with fields: ... | JSON manifest)

## Section Convention
(unnumbered | numbered hierarchical | directory-based)

## Code Examples
(bare inline | fenced blocks | BAD/GOOD pairs with emoji)

## Registry/Index
(what file to update and its format)

## Metadata
(tags, globs, modes, etc.)

## Canonical Domains to Include
(which of the 8 canonical files apply, how to split/combine)

## Special Notes
(any repo-specific conventions, max file sizes, etc.)
```

## Output

- Adapted Snowflake rule files matching target repo format
- PR submitted to target repo
- Updated pr-tracker.md
