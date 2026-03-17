---
name: tape-builder
description: "Build automated Cortex Code demo recordings using VHS (Charmbracelet). Generates .tape files, prerequisite data, and setup scripts for terminal GIF/MP4/WebM recordings. Use when: user wants to record a terminal demo, build a VHS tape, create a GIF demo, record cortex in action, generate a tape file, terminal recording, VHS demo. Triggers: tape builder, vhs demo, vhs tape, record demo, gif demo, terminal recording, tape file, record cortex, build tape."
---

# Cortex Code Tape Builder (VHS)

## Step 0: Check Dependencies

**Goal:** Ensure VHS and its dependencies are installed.

Run these checks silently via Bash. If anything is missing, install it or tell the user how to fix it.

**Required:**
- `vhs` -- Charmbracelet VHS. Install: `brew install vhs`
- `ffmpeg` -- required by VHS. Install: `brew install ffmpeg`
- `ttyd` -- required by VHS. Install: `brew install ttyd`
- `cortex` -- Cortex Code CLI. Must be on PATH.
- `pyyaml` -- Python YAML library. Install: `pip3 install pyyaml`

**Check commands:**
```bash
which vhs && which ffmpeg && which ttyd && which cortex && python3 -c "import yaml"
```

If any are missing, install them automatically (brew/pip) or inform the user if manual steps are needed.

**Also:** The tape generator script is at `scripts/generate_tape.py` within this skill directory. Run it directly from there using its absolute path. All output files (tape, GIF, MP4, prompts YAML, setup scripts) are written to the current working directory.

The script path is: `<SKILL_DIR>/scripts/generate_tape.py` (e.g., `~/.snowflake/cortex/skills/tape-builder/scripts/generate_tape.py`).

---

Build a complete automated demo using VHS -- the declarative terminal recorder by Charmbracelet. This skill walks through an interactive wizard, then generates:

- **`./cortex_demo.tape`** -- VHS tape file (the recording script)
- **`./cortex_demo_prompts.yaml`** -- Prompts file (reusable, can regenerate tape)
- **`./cortex_demo_setup.sql`** -- SQL to create all Snowflake objects
- **`./cortex_demo_setup.py`** -- Python script to generate any local files (PDFs, CSVs) and upload them

## Workflow

```
Step 1: Ask what demo they want
  ↓  STOP — ask user to describe their demo
Step 2: Plan everything (schema, data, products, prompts)
  ↓  STOP — present plan for approval
Step 3: Generate Prerequisites (data, files, Snowflake objects)
  ↓
Step 4: Generate VHS Tape + Prompts YAML
  ↓
Step 5: Run the Demo (record GIF/MP4, dry run, or skip)
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
6. **VHS settings** -- theme, dimensions, typing speed (suggest defaults, user can override)

**STOP: Present the full plan to the user before executing anything.**

Show a clear summary:
- What database/tables will be created
- What data will be synthesized (row counts, document counts)
- The draft list of demo prompts
- What Snowflake products each prompt highlights
- VHS recording settings (theme, output formats)

Ask: "Does this look good? Any changes before I set it up?"

---

## Step 3: Generate Prerequisites

**Goal:** Create all Snowflake objects and local files needed for the demo.

After user confirms the plan, generate and execute:

**`./cortex_demo_setup.sql`** -- SQL setup script:
```sql
-- Cortex Code Demo Setup
-- Generated by tape-builder skill
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

## Step 4: Generate VHS Tape + Prompts YAML

**Goal:** Create `./cortex_demo.tape` and `./cortex_demo_prompts.yaml`.

### Prompt design principles

1. **Sound like a real user** -- Prompts are typed into a coding agent chat. Write them as natural requests, NOT tutorial instructions.
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

### Generate the Prompts YAML

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

### Generate the VHS Tape

Use the generator script to create the tape file from the prompts:

```bash
python3 <SKILL_DIR>/scripts/generate_tape.py ./cortex_demo_prompts.yaml --output ./cortex_demo.tape
```

Generator options:
- `--sleep-per-prompt 240` -- seconds to sleep after each prompt (default: 240)
- `--wait-timeout 30m` -- VHS WaitTimeout setting (default: 30m)
- `--connection devrel` -- Snowflake connection name
- `--theme "Catppuccin Mocha"` -- VHS theme
- `--gif-only` / `--mp4-only` -- restrict output format

Or generate the tape directly by writing `./cortex_demo.tape`. The tape MUST follow this structure:

```tape
# Cortex Code Demo: <Title>
# Generated by tape-builder skill
# Products: <list of products highlighted>
#
# Run: vhs cortex_demo.tape
# Validate: vhs validate cortex_demo.tape

# --- Output ---
Output cortex_demo.gif
Output cortex_demo.mp4

# --- Terminal Settings ---
Require cortex
Set Shell "bash"
Set FontSize 14
Set FontFamily "SF Mono"
Set Width 1400
Set Height 800
Set TypingSpeed 50ms
Set Theme "Catppuccin Mocha"
Set Padding 20
Set WindowBar Colorful
Set WindowBarSize 40
Set WaitTimeout 30m

# --- Launch Cortex ---
Type "cortex --connection <CONNECTION> --bypass --auto-accept-plans --disallowed-tools ask_user_question enter_plan_mode --no-auto-update --session-name 'Demo: <Title>'"
Enter
Sleep 15s
Wait+Screen /\? for help/
Sleep 1s

# --- Prompt 1: <description> ---
Sleep 3s
Type "<prompt text>"
Enter
Sleep 240s

# --- Prompt 2: <description> ---
Sleep 3s
Type "<prompt text>"
Enter
Sleep 240s

# ... repeat for each prompt ...

# --- End ---
Sleep 5s
```

### Critical tape patterns

- **`--bypass`**: Auto-approves ALL tool calls. No permission prompts.
- **`--auto-accept-plans`**: Auto-accepts plan mode. No plan confirmation prompts.
- **`--disallowed-tools ask_user_question enter_plan_mode`**: Prevents the agent from asking clarifying questions or entering plan mode, which would stall the recording.
- **`Wait+Screen /\? for help/`**: Waits until `? for help` appears in the Cortex TUI bottom bar. Used ONLY for initial startup detection. The `?` must be escaped as `\?` since VHS uses regex.
- **`Sleep <N>s` after prompts**: We use Sleep-based waits for prompt responses instead of `Wait+Screen`. This is because VHS screen buffer polling can hang during complex multi-tool Cortex responses with rapid TUI re-renders. `Wait+Screen` works reliably for startup and simple prompts, but is unreliable for longer tool-heavy responses.
- **`Set WaitTimeout 30m`**: Must be set explicitly. VHS has a built-in default timeout (~300s) that will kill the recording if a Wait command takes longer. Use 30m as a safe ceiling.
- **`Sleep 3s` between prompts**: Gives the viewer time to read the response.
- **Timing estimates**: Simple data exploration prompts typically complete in 2-3 min. Complex prompts (building agents, Streamlit apps) may take 5-10 min. Set `Sleep` values with generous buffers -- extra idle time at the end of a response is better than cutting off mid-response.

### Tape customization options

The user may want to adjust:
- **Theme**: `Set Theme "<name>"` -- run `vhs themes` for the full list. Good defaults: "Catppuccin Mocha", "Dracula", "GitHub Dark", "Tokyo Night"
- **Output formats**: Add/remove `Output` lines for `.gif`, `.mp4`, `.webm`
- **Typing speed**: `Set TypingSpeed 50ms` (default) -- lower is faster, higher is more dramatic
- **Dimensions**: `Set Width` / `Set Height` -- 1400x800 is good for 1080p, use 1920x1080 for full HD
- **Font**: `Set FontFamily "SF Mono"` or "JetBrains Mono", "Fira Code", etc.
- **Per-prompt speed**: `Type@100ms "slower prompt"` for dramatic effect

### Validate the tape

Always validate the tape before offering to run it:

```bash
vhs validate ./cortex_demo.tape
```

### Present summary

```
Demo setup complete!

Database: CORTEX_DEMO_<TOPIC>.DEMO
Products highlighted: <list>

Files created:
  ./cortex_demo.tape            -- VHS tape file (run with: vhs cortex_demo.tape)
  ./cortex_demo_prompts.yaml    -- Demo prompts (editable, can regenerate tape)
  ./cortex_demo_setup.sql       -- SQL setup script (re-runnable)
  ./cortex_demo_setup.py        -- Data synthesis script

Output will be:
  ./cortex_demo.gif             -- Animated GIF (shareable, embeddable)
  ./cortex_demo.mp4             -- Video file (higher quality)
```

---

## Step 5: Run the Demo

**Goal:** Offer to launch the VHS recording.

**Action:** Use `ask_user_question`:

```
Everything is set up. Want me to run the demo now?
```

Options:
- Record GIF + MP4 (runs `vhs cortex_demo.tape`)
- Validate only (runs `vhs validate cortex_demo.tape` to check syntax)
- No, I'll run it later

If the user chooses to record:

Run via Bash (background mode):
```bash
vhs /path/to/cortex_demo.tape 2>&1
```

VHS will:
1. Open its own virtual terminal (no Terminal.app window needed)
2. Launch cortex with the specified flags
3. Type each prompt with realistic speed
4. Wait for each response to complete
5. Render the output files (GIF + MP4)

After the run completes, report the result:
- Show output file sizes and paths
- Suggest `open ./cortex_demo.gif` to preview
- Mention `vhs publish ./cortex_demo.gif` for sharing via vhs.charm.sh

If the user declines:
```
To record:     vhs cortex_demo.tape
To validate:   vhs validate cortex_demo.tape
To edit:       Open cortex_demo.tape in any text editor

To regenerate the tape from modified prompts:
  python3 <SKILL_DIR>/scripts/generate_tape.py cortex_demo_prompts.yaml
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

## VHS Quick Reference

### Common Settings
```tape
Set Shell "bash"             # Shell to use
Set FontSize 14              # Font size in pixels
Set FontFamily "SF Mono"     # Font family
Set Width 1400               # Terminal width in pixels
Set Height 800               # Terminal height in pixels
Set TypingSpeed 50ms         # Delay between keystrokes
Set Theme "Catppuccin Mocha" # Color theme (run `vhs themes` for list)
Set Padding 20               # Terminal padding in pixels
Set Framerate 30             # Recording framerate
Set PlaybackSpeed 1.0        # Playback speed multiplier
Set WindowBar Colorful       # Window bar style: Colorful, ColorfulRight, Rings, RingsRight
Set WindowBarSize 40         # Window bar height
Set WaitTimeout 30m              # Timeout for Wait commands (use 30m for Cortex demos)
```

### Key Commands
```tape
Type "text"                  # Type text with TypingSpeed delay
Type@100ms "slow text"       # Type with custom speed
Enter                        # Press Enter
Escape                       # Press Escape
Space                        # Press Space
Ctrl+C                       # Key combo
Sleep 2s                     # Pause for 2 seconds
Wait+Screen /regex/          # Wait until regex matches screen content
Hide                         # Stop recording frames (for setup)
Show                         # Resume recording frames
Screenshot frame.png         # Capture current frame
```

### Output Formats
```tape
Output demo.gif              # Animated GIF (embeddable)
Output demo.mp4              # MP4 video (high quality)
Output demo.webm             # WebM video (web-friendly)
Output frames/               # PNG frame sequence
```

---

## Important Notes

- **Dataset size**: All tables MUST be 10,000 rows or fewer. Prefer 1,000-5,000 rows.
- **Document count**: Generate 10-30 documents maximum for search/parse demos.
- **Prompts per demo**: 4-8 prompts. Fewer is better -- each should be impactful.
- **Disallowed tools in tape**: The tape uses `--disallowed-tools ask_user_question enter_plan_mode` to prevent interactive stalls. The agent still has access to all other tools via `--bypass`.
- **Self-contained**: The demo should work on any Snowflake account with ACCOUNTADMIN. Don't depend on pre-existing objects outside what the setup creates.
- **No secrets**: Don't include passwords, tokens, or connection strings in generated files.
- **Idempotent setup**: Use CREATE OR REPLACE / CREATE IF NOT EXISTS so scripts can be re-run safely.
- **Tape is editable**: Unlike the demo-builder's Python script, `.tape` files are plain text and trivially editable. Encourage users to tweak timing, add pauses, or adjust prompts directly.
- **Wait timeout**: Set `Set WaitTimeout 30m` explicitly. VHS has a built-in default (~300s) that is too short for Cortex demos. Without an explicit setting, long prompts will time out.
- **Wait+Screen limitations**: `Wait+Screen /\? for help/` is reliable for detecting Cortex startup but can hang for complex multi-tool responses. Always use `Sleep <N>s` for prompt response waits.
- **Output paths**: VHS cannot use absolute paths starting with `/` in `Output` and `Screenshot` commands (VHS parses `/` as regex delimiter). Use relative paths only.
- **GIF size**: Long demos produce large GIFs. For demos over 4-5 prompts, suggest MP4 as the primary output and GIF as optional.
