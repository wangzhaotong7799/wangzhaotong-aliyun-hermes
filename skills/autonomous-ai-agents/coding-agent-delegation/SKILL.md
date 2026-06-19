---
name: coding-agent-delegation
description: "Delegate coding tasks to external AI coding CLI agents — Claude Code, OpenAI Codex, or OpenCode. One-shot and interactive modes, PR review, parallel worktrees, session management."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [coding-agent, delegation, automation, orchestration, claude, codex, opencode]
---

# Coding Agent Delegation

Delegate coding tasks to external AI coding-agent CLIs. This umbrella covers the shared orchestration patterns — all three supported agents follow the same shapes for one-shot execution, interactive sessions, PR review, parallel work, and session management.

## When to Use

Use when the user asks you to use an external coding agent (Claude Code, Codex, OpenCode) for implementation, refactoring, code review, or automated PR creation.

## Shared Patterns

All three agents share the same operating principles:

| Pattern | Description |
|---------|-------------|
| **One-shot** | Single command that runs and exits: `agent -p "task"`, `agent exec "task"`, `agent run "task"` |
| **Background/Interactive** | Long-running PTY/tmux session for multi-turn work |
| **PR Review** | Review via diff pipe, PR number, or isolated worktree |
| **Parallel work** | Independent worktrees for concurrent tasks |
| **Session management** | List, resume, continue, cost tracking |
| **Git required** | All three need a git repo (scaffold with `mktemp -d && git init` for scratch work) |

### One-Shot Print Mode (PREFERRED for single tasks)

```bash
# Claude Code
claude -p 'Add error handling to API calls' --max-turns 10

# Codex
codex exec 'Add dark mode toggle'

# OpenCode
opencode run 'Add retry logic to API calls'
```

### Background Mode (Long Tasks)

Start in background with PTY, monitor with process tools:

```bash
terminal(command="codex exec --full-auto 'Refactor auth module'", workdir="~/project", background=true, pty=true)
# Returns session_id → monitor with process(action="poll|log")
```

### PR Review Pattern

```bash
# Via piped diff (all three)
git diff origin/main...feature | claude -p 'Review this diff' --max-turns 1

# Via PR number
opencode pr 42

# Via isolated temp clone
REVIEW=$(mktemp -d) && git clone ... $REVIEW && cd $REVIEW && codex exec 'Review PR #42'
```

### Parallel Work with Worktrees

```bash
git worktree add -b fix/issue-78 /tmp/issue-78 main
git worktree add -b fix/issue-99 /tmp/issue-99 main

terminal(command="codex exec --yolo 'Fix issue #78'", workdir="/tmp/issue-78", background=true, pty=true)
terminal(command="opencode run 'Fix issue #99'", workdir="/tmp/issue-99", background=true, pty=true)
```

## Provider-Specific Details

### Claude Code (`claude`)

**Install:** `npm install -g @anthropic-ai/claude-code`
**Auth:** `claude auth login` or `ANTHROPIC_API_KEY`
**Version:** v2.x+

**Key difference:** Supports `--model`, `--effort`, `--output-format json`, `--json-schema`, `--allowedTools`, `/compact`, `--dangerously-skip-permissions`, custom subagents, MCP integration, hooks system.

**Print mode (preferred):**
```
claude -p 'Add error handling to all API calls' --allowedTools 'Read,Edit' --max-turns 10
```

**Interactive via tmux (for multi-turn work):**
```
terminal(command="tmux new-session -d -s claude-work -x 140 -y 40")
terminal(command="tmux send-keys -t claude-work 'cd /path/to/project && claude' Enter")
```

**Dialog handling in tmux:** Workspace trust → Enter. Permissions bypass → Down then Enter.

**Subcommands:** `-p` (print), `-c` (continue), `-r <id>` (resume), `--fork-session`, `--bare` (fastest, skip plugins/hooks/MCP), `claude doctor` (health check), `claude auth status` (login check).

**Structured output:** `--output-format json` returns session_id, cost, turn count. `--json-schema` forces structured extraction.

### Codex CLI (`codex`)

**Install:** `npm install -g @openai/codex`
**Auth:** `OPENAI_API_KEY` or Codex OAuth session (`~/.codex/auth.json`)
**Version:** Latest

**Key difference:** Requires `pty=true` for all calls. Simpler flag set. `--yolo` = no sandbox, `--full-auto` = sandboxed with auto-approve. Must be in a git repo.

**One-shot:**
```
codex exec 'Build a snake game in Python'
```

**Background with monitoring:**
```
terminal(command="codex exec --full-auto 'Refactor auth module'", workdir="~/project", background=true, pty=true)
process(action="poll", session_id="<id>")
process(action="submit", session_id="<id>", data="yes")  # answer Codex questions
```

**PR Review:** Use temp clone with `codex exec` + `--full-auto`.

### OpenCode CLI (`opencode`)

**Install:** `npm i -g opencode-ai@latest` or `brew install anomalyco/tap/opencode`
**Auth:** `opencode auth login` or provider env vars
**Version:** Latest

**Key difference:** Provider-agnostic (OpenRouter, Anthropic, OpenAI). `opencode run` is the one-shot mode (no pty needed). Interactive TUI sessions require pty. Supports `--model provider/model`, `--thinking`, `--file` for attaching context.

**One-shot:**
```
opencode run 'Add retry logic to API calls' -f config.yaml
```

**Interactive (background + pty):**
```
terminal(command="opencode", workdir="~/project", background=true, pty=true)
process(action="submit", session_id="<id>", data="Implement OAuth refresh flow")
```

**Session management:** `opencode session list`, `opencode stats`, `opencode -c` (continue last).

**Important:** Do NOT use `/exit` — use Ctrl+C (`\x03`) or `process(action="kill")`.

## Verifying Tool Readiness

Before dispatching, verify the target agent is installed:

```bash
# Claude Code
claude --version && claude doctor

# Codex
codex --version

# OpenCode
opencode --version && opencode auth list
```

## Session & Cost Management

| Agent | Session list | Cost/stats | Resume |
|-------|-------------|------------|--------|
| Claude Code | Auto-saved in `.claude/sessions/` | Part of JSON output | `-c` (last), `-r <id>` (specific) |
| Codex | Auto-saved | N/A | N/A |
| OpenCode | `opencode session list` | `opencode stats` | `-c` (last), `-s <id>` (specific) |

## Pitfalls

1. **PTY required for interactive sessions** — Claude Code TUI, Codex interactive, and OpenCode TUI all need a pseudo-terminal. `opencode run` does NOT need pty.
2. **Git repo required** — Codex and OpenCode refuse to run outside a git directory. Claude Code can run without one but works better with it.
3. **PATH mismatch** — Shell environments may resolve different binaries. Use `which -a <agent>` to check.
4. **Dialog handling (Claude Code tmux)** — Workspace trust and permissions dialogs must be handled with `tmux send-keys`.
5. **`--max-turns` is print-mode only** — ignored in interactive sessions for Claude Code.
6. **Don't use `/exit` in OpenCode** — it opens an agent selector. Use Ctrl+C or kill.
7. **Background sessions persist** — always clean up tmux sessions: `tmux kill-session -t <name>`.
8. **No session sharing** — don't share a working directory across parallel agent sessions.
9. **Always use `pty=true` for Codex** — Codex hangs without a PTY.
10. **Cleaning up worktrees** — after parallel tasks, remove worktrees with `git worktree remove <path>`.

## Archived Skills

The former standalone skills `claude-code`, `codex`, and `opencode` have been absorbed into this umbrella. Their full provider-specific detail (CLI flags, all subcommands, edge cases) is preserved in the respective sections above. See `~/.hermes/skills/.archive/` for the original SKILL.md files.
