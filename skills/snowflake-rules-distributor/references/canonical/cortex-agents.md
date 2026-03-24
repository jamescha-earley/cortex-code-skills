# Cortex Agents

## Overview

Cortex Agents combine LLM orchestration with tools (Cortex Analyst for text-to-SQL, Cortex Search for RAG, stored procedures for custom logic). Used by Snowflake Intelligence and the Cortex Agent API.

## Creating an Agent

```sql
CREATE OR REPLACE AGENT my_db.my_schema.sales_agent
FROM SPECIFICATION $$
{
    "models": {"orchestration": "auto"},
    "orchestration": {
        "budget": {"seconds": 900, "tokens": 400000}
    },
    "instructions": {
        "orchestration": "You are SalesBot, a sales intelligence assistant...",
        "response": "Be concise and professional. Use tables for multi-row data."
    },
    "tools": [
        {
            "tool_spec": {
                "type": "cortex_analyst_text_to_sql",
                "name": "SalesOpportunities",
                "description": "Queries Salesforce opportunity data..."
            }
        },
        {
            "tool_spec": {
                "type": "cortex_search",
                "name": "ProductDocSearch",
                "description": "Searches product documentation..."
            }
        }
    ],
    "tool_resources": {
        "SalesOpportunities": {"semantic_model_file": "@stage/sales_model.yaml"},
        "ProductDocSearch": {"name": "db.schema.my_search_service"}
    }
}
$$;
```

### Tool Types

| Type | Purpose |
|------|---------|
| `cortex_analyst_text_to_sql` | Natural language to SQL via semantic model |
| `cortex_search` | Semantic search over documents/records |
| `data_to_chart` | Generate visualizations |
| `code_interpreter` | Execute Python for analysis |
| `generic` | Stored procedures for custom logic |

## Best Practices

### Scoping

- **Start with the top 20 business questions** stakeholders need answered — this defines scope.
- **Favor micro-agents over monolithic agents** — 5-10 tools per agent. Build specialized agents (e.g., "Sales Pipeline Agent", "Customer Usage Agent") rather than one that does everything.
- Work backward from questions to identify required tools and data.

### Tool Descriptions — The Most Critical Factor

Tool descriptions are the single most impactful factor in agent quality. Follow this template:

**[What it does] + [What data it accesses] + [When to use it] + [When NOT to use it]**

BAD:
```
Name: ConsumptionTool
Description: Gets consumption data.
```

GOOD:
```
Name: CustomerConsumptionAnalytics
Description: Analyzes Snowflake consumption metrics for customer accounts
  including credit usage, compute hours, and storage.
Data Coverage: Daily aggregated consumption data, updated nightly. Past 2 years.
When to Use:
- Questions about customer usage patterns, trends, or growth
- Queries about specific customers' consumption
When NOT to Use:
- Real-time data (daily batch, not real-time)
- Individual query performance (use QueryHistory tool)
```

The "When NOT to Use" section is critical — without it, agents try to use tools for everything remotely related.

### Instructions

Split instructions by purpose:

| If it affects... | Put it in... |
|-----------------|-------------|
| Which tool to select | Orchestration instructions |
| What data to retrieve | Orchestration instructions |
| How to sequence tool calls | Orchestration instructions |
| Conditional logic and rules | Orchestration instructions |
| How to format the answer | Response instructions |
| What tone to use | Response instructions |
| What to say on errors | Response instructions |

### Testing

- Build a test set of 50-100 questions covering: in-scope, out-of-scope, edge cases, and variations.
- Track three metrics: **answer_correctness**, **tool_selection_accuracy**, **logical_consistency**.
- Test ambiguous questions that could match multiple tools — these reveal weak tool descriptions.
