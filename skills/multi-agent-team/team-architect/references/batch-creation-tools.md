# Batch Agent Creation — Automation Tools

> **Absorbed from `batch-create-subagents`** (2026-05-22 consolidated into `team-architect`)
>
> This reference documents the batch creation tooling that can supplement the manual team building SOP. Use the SOP in the parent umbrella for quality checks; use these scripts when you need to create many agent stubs at once.

## CLI Batch Create

```bash
cd ~/.hermes/skills/multi-agent-team/
python batch_create_tool.py --template advanced --count 5 --prefix custom_
```

Creates standardized SKILL.md stubs for N agents following the team-architect template format.

## Interactive Wizard

```bash
python interactive_agent_wizard.py
```

Guides through: agent name → role type → description → permission level → generates SKILL.md

## Template Variables

| Variable | Purpose |
|----------|---------|
| `{{agent_name}}` | Agent ID (kebab-case) |
| `{{agent_title}}` | Display name |
| `{{core_role}}` | Core role description |
| `{{domain_keywords}}` | Domain tag list |
| `{{permission_level}}` | none/read-only/restricted/read-write/full |
| `{{concurrency_limit}}` | Max concurrent instances |

## Important Limitation

These scripts create **file stubs only** — they do NOT call `skill_manage(action='create')` to register the agent with the Hermes system. After running the script, you must still call `skill_manage` for each agent, or use the checklist in `team-architect`'s stage six to verify registration.
