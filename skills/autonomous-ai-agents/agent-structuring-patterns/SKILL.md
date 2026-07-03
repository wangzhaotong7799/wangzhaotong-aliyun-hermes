---
name: agent-structuring-patterns
description: Decision framework for structuring Hermes Agent capabilities — when to create a new profile, use in-session skills, delegate to subagents, or keep within the current session. Covers isolation, memory, cron, model, and maintenance trade-offs.
version: 1.0.0
tags:
  - hermes
  - profile
  - architecture
  - subagent
  - delegation
  - decision-framework
triggers:
  - "我该用 profile 还是 skill？"
  - "建一个新的 agent 还是用现有的？"
  - "这个任务应该单开一个 profile 吗？"
  - "怎么组织这个新功能"
  - "用 delegate_task 还是单独 profile？"
  - "should I create a new profile for this"
  - "profile vs skill vs subagent"
---

# Hermes Agent Structuring Patterns

When a user wants to add a new autonomous capability (stock analyst, market monitor, domain expert, automated report runner), you must decide **how to structure it** within Hermes. Four main options, in order of isolation:

| Option | Isolation | Best for |
|--------|-----------|----------|
| **In-session skill** | None — runs in current context | One-off questions, quick analysis |
| **delegate_task subagent** | Short-lived, isolated context | Batch processing, parallel work |
| **Cron job** | Persistent, independent session | Scheduled reports, recurring checks |
| **Dedicated profile** | Fully isolated memory/config/cron | Long-term domain experts, independent personas |

## Decision Tree

```
想加一个新能力？
│
├─ 只是偶尔问一句？ → 加载现有 skill 就够了
│
├─ 定期出报告/定时任务？
│   ├─ 跟现有任务同一领域（如基金、指数）→ 现有 profile + cron
│   └─ 全新领域（如股票、加密货币）→ 新 profile + 独立 cron
│
├─ 需要独立记忆/不能串到日常？
│   └─ 新 profile（记忆完全隔离）
│
└─ 需要不同模型/配置？
    └─ 新 profile（独立 config，不同 provider）
```

## Profile vs In-Session: Full Comparison

| Dimension | Profile | In-Session |
|-----------|---------|------------|
| **Memory** | Fully isolated — no cross-contamination | Shared — stock chatter leaks into daily work |
| **Config** | Independent model, provider, toolsets | Inherits current config |
| **Skills** | Independent skill directory | Shares same skills |
| **Cron** | Independent schedule + delivery | Shares same cron |
| **Personality** | Can have its own SOUL.md (different persona) | Same persona as current session |
| **Access** | `hermes -p name` or gateway per-channel mapping | Same gateway session |
| **Maintenance** | Dual: need to update both profiles | Zero extra maintenance |
| **Creation cost** | ~30 seconds (`hermes profile create`) | Zero |

### When to recommend a new profile

| ✅ Yes | ❌ No |
|--------|-------|
| The domain has its own persistent state to track | User just wants to ask one question |
| Needs different model/provider (e.g. stock analysis uses a cheaper model) | Same model works fine |
| Memory contamination would cause real problems | Domain is closely related to existing work |
| Will have its own cron schedule | Just occasional manual queries |
| User wants a distinct persona/role | Same persona is fine |

## Creating a Profile

```bash
hermes profile create <name>          # Create
hermes -p <name>                      # Enter the new profile
```

Inside the new profile:
1. Load/install relevant skills
2. Set the model (`/model` or `hermes config set model.default ...`)
3. Create SOUL.md (persona definition)
4. Set up cron jobs if needed
5. Configure gateway delivery if chatting across platforms

### Example: Stock Analyst Profile

```bash
hermes profile create stock-analyst
hermes -p stock-analyst
# Inside: set model to deepseek-v4-flash for daily scans
# Create SOUL.md with analyst persona
# Install/copy stock analysis skills
# Set up daily pre-market cron report
```

## Skill Delegation vs Profile vs Subagent

| Need | Tool | Why |
|------|------|-----|
| Quick parallel research | `delegate_task` | Zero setup, isolated per-call |
| Long-running batch job | Background terminal + notify | Hours-long processing |
| Daily/weekly recurring report | Cron job | Autonomous schedule |
| Domain expert with history | Profile | Durable memory, independent |
| Same-domain subtask | In-session /skill load | Instant, same context |

## References

- `references/stock-analyst-profile-example.md` — Concrete example of setting up a stock analyst profile with MoA config, SOUL.md template, daily cron schedule, and fund/stock integration patterns.

## Pitfalls

1. **Profiles are not for one-offs.** If the user won't use it next week, a skill + ad-hoc session is better.
2. **Memory isolation is the strongest reason to create a profile.** If the new capability's context shouldn't mix with daily work (e.g., sensitive financial tracking vs general operations), profile is the right choice.
3. **Model isolation.** Profiles let you use different providers/models per domain — useful when analysis tasks benefit from cheap flash models but aggregations need pro-tier reasoning.
4. **Don't over-profile.** Creating a profile for every small capability leads to maintenance debt. If the domain shares the same model, memory namespace, and cron schedule as existing work, keep it in-session.
5. **Cron belongs to the profile it was created in.** A cron job created under `stock-analyst` profile has its own prompt and delivery targets — it won't affect your default profile's cron list.
