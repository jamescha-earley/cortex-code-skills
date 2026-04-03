---
name: setup-good-morning
description: "Set up the good-morning daily briefing skill from scratch. Walks through Google Workspace MCP installation, Snowflake storage setup, and Google Doc tracking configuration. Use when: user wants to set up good morning, create a daily briefing, configure morning briefing, install good morning skill. Triggers: setup good morning, install good morning, create briefing, setup daily briefing, configure morning briefing, setup-good-morning."
---

# Setup Good Morning — Daily Briefing Wizard

Interactive wizard that sets up the `good-morning` daily briefing skill. Handles all prerequisites: Google Workspace MCP, optional Snowflake snapshot storage, and tracked Google Docs.

After setup, the user can run `$good-morning` each day for a calendar timeline, email triage, and optionally Google Doc change summaries.

---

## Prerequisites Overview

The good-morning skill requires:

1. **Google Workspace MCP** — for reading calendar events, emails, and Google Docs
2. **(Optional) A Snowflake connection** — for storing document snapshots (enables doc change tracking across sessions)
3. **(Optional) Google Doc IDs** — the docs to track for daily diffs (requires #2)

This wizard walks through all of them.

---

## Step 1: Check for Google Workspace MCP

**Goal:** Ensure the Google Workspace MCP server is installed and working.

Read `~/.snowflake/cortex/mcp.json` and check if a `google-workspace` entry exists.

**If the entry exists:**
- Run a quick smoke test by calling `list_calendars` to verify it works.
- If it works, report: "Google Workspace MCP is already configured and working." Move to Step 2.
- If it fails, tell the user the MCP entry exists but isn't connecting, and offer to reinstall.

**If the entry does NOT exist:**

Tell the user:

```
The good-morning skill needs Google Workspace MCP to read your calendar, email, and Google Docs.
Let me walk you through the setup.
```

Then walk through the Google Workspace MCP installation inline:

### 1a. Install the Google Workspace MCP Server

The Google Workspace MCP server provides 45+ tools for Google Docs, Sheets, Drive, Slides, Gmail, and Calendar.

**Installation steps:**

1. Check if Node.js is installed:
   ```bash
   node --version
   ```
   If not installed, tell the user: "Node.js is required. Install it from https://nodejs.org/ (v18+) and re-run this setup."

2. Install the MCP server globally:
   ```bash
   npm install -g @anthropic/google-workspace-mcp
   ```

3. The server needs Google OAuth credentials. Tell the user:

   ```
   To connect to Google Workspace, you need OAuth credentials:

   1. Go to https://console.cloud.google.com/
   2. Create a new project (or select an existing one)
   3. Enable these APIs:
      - Gmail API
      - Google Calendar API
      - Google Docs API
      - Google Drive API
      - Google Slides API
      - Google Sheets API
   4. Go to "Credentials" → "Create Credentials" → "OAuth 2.0 Client ID"
      - Application type: "Desktop app"
      - Name: "Cortex Code Google Workspace"
   5. Download the JSON file — you'll need the client_id and client_secret from it
   ```

   **STOP**: Wait for the user to provide their `client_id` and `client_secret`.

4. Store the credentials as secrets:
   ```bash
   echo "<client_id>" > /tmp/gw_client_id.txt
   cortex secret store google_workspace_client_id --from-file /tmp/gw_client_id.txt
   rm /tmp/gw_client_id.txt

   echo "<client_secret>" > /tmp/gw_client_secret.txt
   cortex secret store google_workspace_client_secret --from-file /tmp/gw_client_secret.txt
   rm /tmp/gw_client_secret.txt
   ```

5. Add the MCP server to Cortex Code config. Read `~/.snowflake/cortex/mcp.json`, add the google-workspace entry:

   ```json
   {
     "google-workspace": {
       "command": "npx",
       "args": ["-y", "@anthropic/google-workspace-mcp"],
       "env": {
         "GOOGLE_CLIENT_ID": "<google_workspace_client_id>",
         "GOOGLE_CLIENT_SECRET": "<google_workspace_client_secret>"
       }
     }
   }
   ```

   Use the Edit tool to add this entry to the existing `mcp.json` (or create the file if it doesn't exist).

6. Start the MCP server to trigger the OAuth flow:
   ```bash
   cortex mcp start
   ```

   This will open a browser window for the user to authenticate with Google. After authenticating, the server stores a refresh token locally.

7. Verify by calling `list_calendars`. If it returns calendars, the setup worked.

**If the MCP server fails to install or authenticate, STOP here.** The rest of the wizard depends on Google Workspace access.

Tell the user they need to restart Cortex Code after MCP setup for the tools to be available in their session. If they just installed it, ask them to restart and re-run `$setup-good-morning`.

---

## Step 2: Configure Email Triage

**Goal:** Set the user's company email domain so the briefing can classify internal vs external emails.

Ask:

```
What's your company email domain? (e.g., snowflake.com, acme.com)
This helps the briefing separate internal/actionable emails from external promos.
```

Store this for the config. Default classification rules:
- **Actionable:** emails from `@{domain}`, direct messages, GitHub notifications, service tickets
- **Skip:** promotional, newsletters, marketing, automated digests from external services

---

## Step 3: Google Doc Tracking (Optional)

**Goal:** Ask if the user wants doc change tracking, and if so, set up storage and collect doc URLs.

Ask using `ask_user_question`:

```
Do you want to track Google Doc changes in your daily briefing?
This shows what changed in specific docs since your last check.
It requires a Snowflake database to store snapshots.
```

Options:
- **Yes, set it up** — enables doc diff tracking with Snowflake storage
- **No, skip for now** — briefing will just do calendar + email (can add later)

### If the user says NO:

Set `doc_tracking_enabled = false`. Skip to Step 4. The generated good-morning skill will only include Phase 1 (Calendar) and Phase 2 (Email Triage).

### If the user says YES:

#### 3a. Choose Snowflake Connection and Storage

Run:
```bash
cortex connections list
```

Show the available connections and ask the user which one to use. If there's only one, suggest it as the default.

Then ask:

```
Which database and schema should good-morning use for storing doc snapshots?
(e.g., MY_DB.PUBLIC — the skill will create one small table there)
```

#### 3b. Create the Snapshot Table

Run against the chosen connection:

```sql
CREATE TABLE IF NOT EXISTS {DB}.{SCHEMA}.GOOD_MORNING_DOC_SNAPSHOTS (
    DOC_ID VARCHAR NOT NULL,
    DOC_NAME VARCHAR,
    CONTENT VARCHAR(16777216),
    CHECKED_AT TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    CONTENT_HASH VARCHAR
);
```

Verify it was created:

```sql
DESCRIBE TABLE {DB}.{SCHEMA}.GOOD_MORNING_DOC_SNAPSHOTS;
```

#### 3c. Add Tracked Google Docs

Ask:

```
Paste the URLs of Google Docs you want to track for daily changes.
(One per line, or comma-separated. You can always add more later.)

Example: https://docs.google.com/document/d/1abc.../edit
```

**STOP**: Wait for the user to provide URLs.

For each URL provided:

1. Parse the doc ID from the URL using the pattern: `/document/d/<DOC_ID>/`
2. Fetch the doc title using `get_document_info` with the parsed ID
3. If the fetch fails, warn the user and skip that doc

Show the parsed list for confirmation:

```
Found these docs:

1. "Q2 Planning Doc" — 1abc...xyz
2. "Team Standup Notes" — 2def...uvw

Look good?
```

**STOP**: Wait for user confirmation. They can remove items or add more.

If the user doesn't have any docs to track yet, that's fine — they can add docs later by editing `config.yaml`.

---

## Step 4: Write the Good Morning Skill

**Goal:** Create the `good-morning` skill directory with SKILL.md and config.yaml.

### 4a. Create the Directory

```bash
mkdir -p ~/.snowflake/cortex/skills/good-morning
```

### 4b. Write config.yaml

Write `~/.snowflake/cortex/skills/good-morning/config.yaml`.

**If doc tracking is enabled:**

```yaml
# Good Morning Skill Configuration

# Company email domain for triage classification
email:
  domain: {DOMAIN}
  max_unread: 20

# Storage for doc snapshots
storage:
  database: {DB}
  schema: {SCHEMA}
  connection: {CONNECTION}

# Google Docs to track for diffs
tracked_docs:
  - id: "{DOC_ID_1}"
    name: "{DOC_NAME_1}"
    url: "https://docs.google.com/document/d/{DOC_ID_1}/edit"
  # ... one entry per tracked doc
```

**If doc tracking is disabled:**

```yaml
# Good Morning Skill Configuration

# Company email domain for triage classification
email:
  domain: {DOMAIN}
  max_unread: 20

# Doc tracking is disabled. To enable it later, add:
# storage:
#   database: MY_DB
#   schema: PUBLIC
#   connection: my_connection
#
# tracked_docs:
#   - id: "<google_doc_id>"
#     name: "Human-readable name"
#     url: "https://docs.google.com/document/d/<id>/edit"
```

### 4c. Write SKILL.md

Write `~/.snowflake/cortex/skills/good-morning/SKILL.md` with the full good-morning skill content.

**If doc tracking is enabled**, include all phases (Calendar, Email, Doc Diffs, Summary).

**If doc tracking is disabled**, include Phase 1 (Calendar), Phase 2 (Email Triage), and Summary. Omit all doc diff logic, the snapshot table bootstrap, and any references to Snowflake storage.

The generated SKILL.md must use the following structure. Replace all placeholders with actual values — no placeholders should remain in the final file.

#### SKILL.md Template (full version with doc tracking):

The frontmatter:
```yaml
---
name: good-morning
description: "Daily morning briefing: calendar summary, email triage, and Google Doc diffs for tracked docs. Use when: user wants a morning briefing, daily summary, start their day, check what's new. Triggers: good morning, morning briefing, start my day, daily briefing, gm, good-morning."
---
```

The body should include:

1. **Introduction** — "A quick daily rundown: today's calendar, actionable emails, and changes to tracked Google Docs since the last check."
2. **Read config** — "Read `config.yaml` from this skill's directory at the start."
3. **First Run: Bootstrap Storage** — CREATE TABLE IF NOT EXISTS for the snapshot table (only if doc tracking enabled)
4. **Phase 1: Calendar** — Fetch today's events via `list_events`, present as a scannable timeline. Flag overlaps with warning emoji. Note free blocks longer than 1 hour. Highlight the marquee event (fewest attendees that user organized, or any event with `[LIVE]` in the title).
5. **Phase 2: Email Triage** — Fetch unread emails via `list_emails` with `label_ids: ["INBOX", "UNREAD"]`. Split into Actionable (from @{DOMAIN}, direct messages, GitHub notifications, service tickets) and Skip (promotional, newsletters, external automated digests). Show actionable as a numbered list with sender, subject, and 1-line snippet. Show skip count only.
6. **Phase 3: Google Doc Diffs** (only if doc tracking enabled) — For each tracked doc: read current content via `read_document`, compute SHA-256 hash (first 64 hex chars), check last snapshot in Snowflake, compare hashes. If no previous snapshot, store baseline. If hash matches, report no changes. If hash differs, summarize changes in 3-8 bullet points (new sections, action items, status changes, new names/dates). Always store new snapshot via INSERT. Escape single quotes in content. Truncate if over 16MB.
7. **Phase 4: Summary Card** — Compact summary with meeting count, conflict flag, actionable/skipped email counts, docs checked/changed counts.
8. **Stopping Points** — None, runs end-to-end.
9. **Configuration** — How to add/remove tracked docs by editing config.yaml. Snapshot cleanup SQL.
10. **Output** — List what the skill produces.

---

## Step 5: Test Run

**Goal:** Verify the skill works end-to-end.

Tell the user:

```
Setup is complete! Let me do a quick test to make sure everything is connected.
```

Run each phase as a verification:

1. Fetch today's calendar events via `list_events` — verify it returns data
2. Fetch unread emails via `list_emails` — verify it returns data
3. If doc tracking enabled: read each tracked Google Doc via `read_document` — verify each succeeds
4. If doc tracking enabled: store initial snapshots in Snowflake — verify inserts succeed

If any phase fails, diagnose and fix:
- Calendar/email failures → Google Workspace MCP issue, check mcp.json and restart
- Doc read failures → check doc ID, verify sharing permissions (doc must be accessible to the authenticated Google account)
- Snapshot storage failures → check Snowflake connection and table permissions

---

## Step 6: Summary

Show the setup summary:

```
=== Good Morning Setup Complete ===

Google Workspace MCP: connected
Email domain:         {DOMAIN}
Doc tracking:         {enabled/disabled}
{If enabled:}
  Snowflake storage:  {DB}.{SCHEMA} on connection "{CONNECTION}"
  Tracked docs:       {N} docs configured
  Snapshot table:     GOOD_MORNING_DOC_SNAPSHOTS

To run your briefing:
  $good-morning

To add more tracked docs later, edit:
  ~/.snowflake/cortex/skills/good-morning/config.yaml

To schedule automatic morning briefings, use:
  /loop "Run $good-morning" every weekday at 9am
```

---

## Stopping Points

- **After Step 1:** If Google Workspace MCP fails to install or the user needs to restart Cortex Code
- **After Step 1a.3:** Wait for user to provide OAuth credentials
- **After Step 3:** Wait for user decision on doc tracking
- **After Step 3c:** Wait for user to provide doc URLs and confirm the list
- **After Step 4:** Confirm the generated config before proceeding to test
- **After Step 5:** Report test results

---

## Output

- `~/.snowflake/cortex/skills/good-morning/SKILL.md` — the daily briefing skill
- `~/.snowflake/cortex/skills/good-morning/config.yaml` — user-specific configuration
- (If doc tracking enabled) `{DB}.{SCHEMA}.GOOD_MORNING_DOC_SNAPSHOTS` — Snowflake table for doc change tracking
- Google Workspace MCP installed and verified (if not already present)
