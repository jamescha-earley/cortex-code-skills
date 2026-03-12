---
name: demo-builder
description: "Build automated Cortex Code demo YAML files with prerequisite data and setup scripts. Use when: user wants to create a demo, build a demo, generate demo prompts, set up a demo environment, prepare a demo, create sample data for a demo, synthesize demo data, build a showcase, create a walkthrough, or generate a cortex demo. Triggers: demo builder, build demo, create demo, demo prompts, demo yaml, demo setup, synthesize data, demo data, showcase, walkthrough, cortex demo."
---

# Cortex Code Demo Builder

## Step 0: Check Dependencies

**Goal:** Ensure all tools the demo script needs are installed before doing anything else.

Run these checks silently via Bash. If anything is missing, install it or tell the user how to fix it.

**Required:**
- `tmux` -- terminal multiplexer. Install: `brew install tmux`
- `ffmpeg` -- screen recording. Install: `brew install ffmpeg`
- `cortex` -- Cortex Code CLI. Must be on PATH.
- `pyyaml` -- Python YAML library. Install: `pip3 install pyyaml`

**Check commands:**
```bash
which tmux && which ffmpeg && which cortex && python3 -c "import yaml"
```

If any are missing, install them automatically (brew/pip) or inform the user if manual steps are needed (e.g., cortex CLI install, granting Screen Recording permission to Terminal.app).

**Also:** The demo recording script is at `scripts/cortex_demo.py` within this skill directory. Run it directly from there using its absolute path -- no need to copy it. All output files (MP4, prompts YAML, setup scripts) are written to the current working directory.

The script path is: `<SKILL_DIR>/scripts/cortex_demo.py` (e.g., `~/.snowflake/cortex/skills/demo-builder/scripts/cortex_demo.py`).

---

Build a complete automated demo for `cortex_demo.py` -- the screen-recording demo script. This skill walks through an interactive wizard, then generates:

- **`./cortex_demo_prompts.yaml`** -- Prompts file for the demo script
- **`./cortex_demo_setup.sql`** -- SQL to create all Snowflake objects (database, schema, tables, stages, etc.)
- **`./cortex_demo_setup.py`** -- Python script to generate any local files (PDFs, CSVs) and upload them

## Workflow

```
Step 1: Ask what demo they want
  ↓  STOP — ask user to describe their demo
Step 2: Plan everything (schema, data, products, prompts)
  ↓  STOP — present plan for approval
Step 3: Generate Prerequisites (data, files, Snowflake objects)
  ↓
Step 4: Generate Demo YAML
  ↓
Step 5: Run the Demo (record MP4, dry run, or skip)
  ↓  STOP — ask user
Done
```

---

## Step 1: Ask What Demo They Want

**Goal:** Get a free-form description of the demo from the user.

**Action:** Ask ONE open-ended question. Do NOT use `ask_user_question` with multiple-choice options. Just ask directly in your message:

"What kind of demo do you want to build?

To plan the best demo, it helps to know:
- **Who is the audience?** (e.g., CTO, data engineers, sales prospects, conference attendees)
- **What Snowflake features do you want to highlight?** (e.g., Cortex AI functions, Dynamic Tables, Streamlit, Cortex Search, data governance)
- **What domain or scenario?** (e.g., analyzing customer reviews, building a data pipeline, searching financial documents)
- **Do you have existing data or should I create sample data?**

You don't need all of these -- just describe what you're going for and I'll figure out the rest."

Do NOT ask about these as separate follow-up questions. Let the user answer as much or as little as they want in one response.

From their description, YOU figure out everything:
- What vertical/domain to use for realistic data
- Which Snowflake products to showcase (use the Product Reference below)
- What data is needed (tables, documents, etc.)
- Whether to synthesize data or ask if they have existing data

If their response is missing critical info you need to plan (e.g., they said "a demo" with no details), ask follow-up questions to fill in the gaps. But if you have enough to work with, go straight to Step 2.

---

## Step 2: Plan Everything

**Goal:** Design the complete demo based on the user's description.

Based on what the user described, plan:

1. **Database and schema** (suggest: `CORTEX_DEMO_<TOPIC>`)
2. **Tables** -- schemas with column names, types, and row counts (cap at 10,000 rows per table, prefer 1,000-5,000)
3. **Documents** -- if needed for search/parse demos, plan 10-30 files
4. **Additional objects** -- stages, dynamic tables, search services, semantic views, etc.
5. **Demo prompts** -- 4-8 prompts that tell a cohesive story, each showcasing a product

**STOP: Present the full plan to the user before executing anything.**

Show a clear summary:
- What database/tables will be created
- What data will be synthesized (row counts, document counts)
- The draft list of demo prompts
- What Snowflake products each prompt highlights

Ask: "Does this look good? Any changes before I set it up?"

---

## Step 3: Generate Prerequisites

**Goal:** Create all Snowflake objects and local files needed for the demo.

After user confirms the plan, generate and execute:

**`./cortex_demo_setup.sql`** -- SQL setup script:
```sql
-- Cortex Code Demo Setup
-- Generated by demo-builder skill
-- Re-runnable: uses CREATE OR REPLACE / IF NOT EXISTS

CREATE DATABASE IF NOT EXISTS CORTEX_DEMO_<TOPIC>;
USE DATABASE CORTEX_DEMO_<TOPIC>;
CREATE SCHEMA IF NOT EXISTS DEMO;
USE SCHEMA DEMO;

-- Tables
CREATE OR REPLACE TABLE ... (...);

-- Stages (if documents needed)
CREATE OR REPLACE STAGE DEMO_DOCS ENCRYPTION = (TYPE = 'SNOWFLAKE_SSE');
```

**`./cortex_demo_setup.py`** -- Python setup script for data synthesis:
```python
#!/usr/bin/env python3
"""Generate demo data for Cortex Code demo"""
# Generates: synthetic table data (INSERT statements), local files (PDFs/text) if needed
```

**Execution order:**
1. Run SQL setup to create database/schema/tables/stages
2. Run Python script to generate synthetic data locally if needed
3. Load data into tables (INSERT or COPY INTO)
4. Upload documents to stage (PUT) if applicable
5. Create derived objects (dynamic tables, search services, semantic views) if applicable

**Data synthesis guidelines:**
- Use `snowflake_sql_execute` to run SQL directly
- For local files (PDFs, CSVs), use `Write` tool or Python via `Bash`
- For PDFs: use Python `reportlab` or simple text files
- For stage uploads: `PUT file:///path/to/file @STAGE_NAME` via SQL
- Prefer INSERT statements for small datasets over CSV+COPY workflows
- For tables under 1000 rows, use INSERT ... SELECT with GENERATOR

**Verify after setup:**
```sql
SELECT table_name, row_count FROM information_schema.tables
WHERE table_schema = 'DEMO' ORDER BY table_name;
```

---

## Step 4: Generate Demo YAML

**Goal:** Create `./cortex_demo_prompts.yaml` with the planned prompts.

### Prompt design principles

1. **Sound like a real user** -- Prompts are typed into a coding agent chat. Write them as natural requests, NOT tutorial instructions. They should sound like someone asking for help, not a teacher giving an assignment.
   - GOOD: "Run sentiment analysis on the customer reviews table"
   - BAD: "Show me how to use AI_SENTIMENT to analyze customer reviews and explain the results"
   - GOOD: "Make this agent available in Snowflake Intelligence"
   - BAD: "Show me how to make this agent available in Snowflake Intelligence so the whole support team can use it from the Snowsight UI"
   - GOOD: "Build a Streamlit dashboard showing revenue by region"
   - BAD: "Create a Streamlit application that visualizes revenue metrics broken down by geographic region with interactive filters"
2. **Start simple** -- First prompt should be exploratory ("Show me what data we have" or "What tables exist in ...?")
3. **Build complexity** -- Each prompt builds on the previous, introducing a new product
4. **Tell a story** -- Follow a narrative arc for the industry/scenario
5. **One product per prompt** -- Each prompt primarily showcases one product
6. **Be specific** -- Reference actual table and column names from the created schema
7. **Keep prompts short** -- One sentence, casual tone. Think Slack message, not email.
8. **End strong** -- Last prompt should be impressive (Streamlit dashboard, Cortex Agent, insightful analysis)

### Generate the YAML

Write `./cortex_demo_prompts.yaml` using this exact format:

```yaml
# Healthcare Support Agent Demo
# Products: Cortex Search, Cortex Agents, Semantic Views, Streamlit
prompts:
  - What tables do we have in CORTEX_DEMO_HEALTHCARE.DEMO?
  - Run sentiment analysis on the patient feedback in the REVIEWS table
  - Create a Cortex Search service over the policy documents in @DEMO_DOCS
  - Build a support agent that can answer questions about our policies
  - Make this agent available in Snowflake Intelligence
  - Build a Streamlit dashboard showing patient satisfaction trends
```

- The file must have a top-level `prompts:` key with a list of strings
- Each prompt is a single line (no multiline)
- 4-8 prompts following the design principles above
- Each prompt should reference real objects created in Step 3

Present a summary:
```
Demo setup complete!

Database: CORTEX_DEMO_<TOPIC>.DEMO
Products highlighted: <list>

Files created:
  ./cortex_demo_prompts.yaml    -- Demo prompts (N prompts)
  ./cortex_demo_setup.sql       -- SQL setup script (re-runnable)
  ./cortex_demo_setup.py        -- Data synthesis script
```

---

## Step 5: Run the Demo

**Goal:** Offer to launch the demo recording immediately.

**Action:** Use `ask_user_question`:

```
Everything is set up. Want me to run the demo now?
```

Options:
- Record MP4 (runs cortex_demo.py with screen recording)
- Dry run without recording (runs with --no-record to test prompts first)
- No, I'll run it later

If the user chooses to run:

1. **Record MP4**: Run via Bash (background mode):
   ```bash
   python3 <SKILL_DIR>/scripts/cortex_demo.py 2>&1
   ```
   Opens Terminal.app, launches cortex, types all prompts, records to `./cortex_demo.mp4`.

2. **Dry run**: Run via Bash (background mode):
   ```bash
   python3 <SKILL_DIR>/scripts/cortex_demo.py --no-record 2>&1
   ```
   Same flow, no recording. Good for testing prompt quality first.

After the run completes, report the result:
- If MP4 recorded: show file size/path, suggest `open ./cortex_demo.mp4`
- If dry run: report whether all prompts completed

If the user declines:
```
To record:    python3 <SKILL_DIR>/scripts/cortex_demo.py
To dry run:   python3 <SKILL_DIR>/scripts/cortex_demo.py --no-record
```

---

## Product Reference

Use this reference to map the user's description to specific Snowflake products. This is for YOUR use when planning -- do NOT present this catalog to the user.

### Cortex AI
| Product | What it does | Data needed |
|---------|-------------|-------------|
| AI_COMPLETE | LLM text generation/chat | Text column or prompt |
| AI_CLASSIFY | Classify text into categories | Text column + category list |
| AI_EXTRACT | Extract structured fields from text | Text column + field names |
| AI_SENTIMENT | Sentiment scoring | Text column (reviews, feedback) |
| AI_SUMMARIZE | Summarize long text | Long text column |
| AI_TRANSLATE | Translate between languages | Text column |
| AI_EMBED | Vector embeddings | Text column |
| AI_PARSE_DOCUMENT | Extract text from PDFs/images | Files on a stage |
| AI_REDACT | Redact PII from text | Text with PII |
| AI_FILTER | Filter content by criteria | Text column |
| AI_AGG | Aggregate/summarize text groups | Text column + grouping |
| Cortex Agents | Multi-tool AI agents | Semantic views or search services |
| Cortex Search Service | Semantic search over documents | Documents on a stage |
| Semantic Views (Cortex Analyst) | Natural language to SQL | Tables + semantic view YAML |

### Data Engineering
| Product | Data needed |
|---------|-------------|
| Dynamic Tables | Source tables with data |
| Iceberg Tables | External volume + data |
| Streams & Tasks | Source tables |

### Data Apps
| Product | Data needed |
|---------|-------------|
| Streamlit | Tables to visualize |
| SPCS | Docker image |
| React/Next.js | API-accessible tables |

### Data Governance
| Product | Data needed |
|---------|-------------|
| Masking Policies | Tables with sensitive columns (email, SSN, phone) |
| Row Access Policies | Tables with role-based rows |
| Data Classification | Tables with PII-like columns |
| Data Quality (DMFs) | Tables to monitor |
| Lineage | Existing pipeline objects |
| Trust Center | Account-level (no data needed) |

### Ecosystem
| Product | Data needed |
|---------|-------------|
| dbt | Source tables + dbt project |
| Notebooks | Tables or data to explore |

### Other
| Product | Data needed |
|---------|-------------|
| Cost Management | Account-level (no data needed) |
| Data Clean Rooms | Shared tables |
| Snowflake Postgres | Tables |

---

## Important Notes

- **Dataset size**: All tables MUST be 10,000 rows or fewer. Prefer 1,000-5,000 rows.
- **Document count**: Generate 10-30 documents maximum for search/parse demos.
- **Prompts per demo**: 4-8 prompts. Fewer is better -- each should be impactful.
- **Allowed tools in demo**: The demo script uses `--allowed-tools` whitelist. Prompts must only require whitelisted tools: Read, Glob, Grep, web_search, web_fetch, data_diff, fdbt, sql, Bash (limited), skill, task, notebook_actions, Edit, Write.
- **Self-contained**: The demo should work on any Snowflake account with ACCOUNTADMIN. Don't depend on pre-existing objects outside what the setup creates.
- **No secrets**: Don't include passwords, tokens, or connection strings in generated files.
- **Idempotent setup**: Use CREATE OR REPLACE / CREATE IF NOT EXISTS so scripts can be re-run safely.
