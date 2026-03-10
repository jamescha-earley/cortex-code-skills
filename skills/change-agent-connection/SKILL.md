---
name: change-agent-connection
description: "Switch the active Snowflake agent connection. Use when: user wants to change which Snowflake account the agent uses, switch the agent's connection, or point the agent at a different environment. Does NOT handle SQL-level connection objects (CREATE CONNECTION). Triggers: change agent connection, switch agent connection, agent connection, change cortex connection, switch cortex connection, use a different account, change active connection."
---

# Change Agent Connection

Changes the persistent agent connection by updating `cortexAgentConnectionName` in `~/.snowflake/cortex/settings.json`.

Only modifies the agent connection. Does NOT touch `sqlConnectionName`.

## Workflow

### Step 1: List Available Connections

Run:
```bash
cortex connections list
```

Parse the JSON output to get:
- `active_connection`: the currently active connection name
- `connections`: map of connection names to their details (account, user, role)

### Step 2: Read Current Settings

Read `~/.snowflake/cortex/settings.json` to find the current value of `cortexAgentConnectionName`.

### Step 3: Present Options

Present the available connections to the user using AskUserQuestion. For each connection show its name, account, and role. Mark which one is currently the agent connection.

**STOP**: Wait for user selection.

### Step 4: Update settings.json

Read `~/.snowflake/cortex/settings.json`, update only `cortexAgentConnectionName` to the selected connection name. Write the file back preserving all other fields.

### Step 5: Apply In-Session

Also run:
```bash
cortex connections set <selected_connection_name>
```

This ensures the current session picks up the change without requiring a restart.

### Step 6: Confirm

Read `~/.snowflake/cortex/settings.json` one more time and verify `cortexAgentConnectionName` was written correctly. Report the change to the user, noting they may need to start a new session for the change to fully take effect.

## Stopping Points

- After Step 3: Wait for user to pick a connection

## Output

`cortexAgentConnectionName` in `~/.snowflake/cortex/settings.json` is updated. User is informed of the change and any restart requirements.
