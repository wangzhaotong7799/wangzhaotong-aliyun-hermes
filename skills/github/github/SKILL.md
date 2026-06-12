---
name: github
description: "GitHub lifecycle: authentication, issues, PR workflow, code review, and repository management via gh CLI or git+curl." 
version: 2.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [GitHub, Pull-Requests, Issues, Code-Review, Repositories, Git, CI/CD]
    related_skills: [codebase-inspection]
---

# GitHub — Complete Lifecycle

Consolidated guide for all GitHub operations: authentication, issues, pull requests, code review, and repository management. Each section covers commands via `gh` CLI first, then `git` + `curl` fallback.

## Shared Auth Setup

Every GitHub operation needs authentication. This section is shared across all subsequent operations — run it once.

### Quick Auth Detection

```bash
if command -v gh &>/dev/null && gh auth status &>/dev/null; then
  AUTH="gh"
else
  AUTH="git"
  if [ -z "$GITHUB_TOKEN" ]; then
    if [ -f ~/.hermes/.env ] && grep -q "^GITHUB_TOKEN=" ~/.hermes/.env; then
      GITHUB_TOKEN=$(grep "^GITHUB_TOKEN=" ~/.hermes/.env | head -1 | cut -d= -f2 | tr -d '\n\r')
    elif grep -q "github.com" ~/.git-credentials 2>/dev/null; then
      GITHUB_TOKEN=$(grep "github.com" ~/.git-credentials 2>/dev/null | head -1 | sed 's|https://[^:]*:\([^@]*\)@.*|\1|')
    fi
  fi
fi
echo "Auth method: $AUTH"
```

### Extract Owner/Repo from Git Remote

```bash
REMOTE_URL=$(git remote get-url origin)
OWNER_REPO=$(echo "$REMOTE_URL" | sed -E 's|.*github\.com[:/]||; s|\.git$||')
OWNER=$(echo "$OWNER_REPO" | cut -d/ -f1)
REPO=$(echo "$OWNER_REPO" | cut -d/ -f2)
echo "Owner: $OWNER, Repo: $REPO"
```

### Using the Shared Auth Script

The helper script `scripts/gh-env.sh` sets all variables (`GH_AUTH_METHOD`, `GITHUB_TOKEN`, `GH_USER`, `GH_OWNER`, `GH_REPO`) in one source:

```bash
source "${HERMES_HOME:-$HOME/.hermes}/skills/github/github/scripts/gh-env.sh"
```

### GitHub Auth Setup (First Time)

If authentication isn't configured, see `references/github-auth.md` for:
- **HTTPS with Personal Access Token** — most portable
- **SSH Key Authentication** — preferred for private repos
- **gh CLI setup** — simplest for interactive use
- **Token extraction from git credentials**

---

## 1. Repository Management

Create, clone, fork, and configure repositories. See `references/repo-management.md` for full details.

### Cloning

```bash
# HTTPS
git clone https://github.com/owner/repo.git
# SSH (if configured)
git clone git@github.com:owner/repo.git
# gh shorthand
gh repo clone owner/repo
```

### Creating Repos

```bash
# gh
gh repo create my-project --public --clone

# curl
curl -s -X POST -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/user/repos \
  -d '{"name": "my-project", "private": false}'
```

### Forking & Sync

```bash
gh repo fork owner/repo --clone
# Keep fork in sync
git fetch upstream && git merge upstream/main && git push
```

### Releases

```bash
gh release create v1.0.0 --title "v1.0.0" --generate-notes
```

### Secrets and Workflows

```bash
gh secret set API_KEY --body "value"
gh workflow list
gh workflow run ci.yml --ref main
```

### Branch Protection

```bash
curl -s -X PUT -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/$OWNER/$REPO/branches/main/protection \
  -d '{"required_status_checks": {"strict": true, "contexts": ["ci/test"]}}'
```

### Emergency Secret Cleanup

When `.env` or secrets get committed, scrub history with `git-filter-repo`:

```bash
pip install git-filter-repo
cd /path/to/repo
git filter-repo --path .env --invert-paths --force
git remote add origin <url>
git push --force --set-upstream origin main
```

See `references/git-filter-repo-cheatsheet.md` for full commands.

### API Cheatsheet

See `references/github-api-cheatsheet.md` for a complete REST API endpoint reference covering repos, PRs, issues, workflows, releases, secrets, and branch protection.

---

## 2. Issue Management

Create, triage, label, assign, and search GitHub issues. See `references/issues.md` for full details.

### Listing Issues

```bash
gh issue list
gh issue list --state open --label bug
gh issue view 42
```

### Creating Issues

```bash
gh issue create --title "Login redirect bug" \
  --body "## Description\n..." --label "bug,backend" --assignee username
```

### Templates

- `templates/bug-report.md` — structured bug report template
- `templates/feature-request.md` — feature request with motivation, solution, alternatives

### Managing Issues

```bash
gh issue edit 42 --add-label "priority:high" --add-assignee username
gh issue comment 42 --body "Root cause found."
gh issue close 42 --reason "not planned"
```

### Bulk Operations

```bash
gh issue list --label "wontfix" --json number --jq '.[].number' | \
  xargs -I {} gh issue close {} --reason "not planned"
```

---

## 3. PR Workflow

Full pull request lifecycle: branch, commit, open, CI, merge. See `references/pr-workflow.md` for complete details.

### Branch and Commit

```bash
git checkout main && git pull origin main
git checkout -b feat/my-feature
# ... make changes with file tools ...
git add src/file.py && git commit -m "feat: description"
git push -u origin HEAD
```

Conventional commits: `feat:`, `fix:`, `refactor:`, `docs:`, `test:`, `ci:`, `chore:`, `perf:`. See `references/conventional-commits.md`.

### Create PR

```bash
gh pr create --title "feat: description" \
  --body "$(cat templates/pr-body-feature.md)" \
  --label enhancement
```

Templates: `templates/pr-body-feature.md`, `templates/pr-body-bugfix.md`.

### Monitor CI

```bash
gh pr checks --watch
# Or curl:
curl -s -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/$OWNER/$REPO/commits/$(git rev-parse HEAD)/status
```

See `references/ci-troubleshooting.md` for diagnosis of common CI failures (tests, lint, types, build, timeouts).

### Auto-Fix CI Loop

1. Check CI → identify failures
2. Read failure logs → understand error
3. Fix code with patch/write_file → commit → push
4. Wait for CI → re-check
5. Repeat up to 3 attempts if still failing

### Merging

```bash
gh pr merge --squash --delete-branch
```

### Complete Workflow

```bash
git checkout main && git pull origin main
git checkout -b fix/my-bug
# Agent makes changes, commits
git push -u origin HEAD
gh pr create --title "fix: description" --body "..."
gh pr checks --watch
gh pr merge --squash --delete-branch
```

---

## 4. Code Review

Review local changes (pre-push) or open PRs. Submit formal reviews with inline comments. See `references/code-review.md` for full details.

### Review Local Changes

```bash
# Scope of changes
git diff main...HEAD --stat
git log main..HEAD --oneline

# Full diff
git diff main...HEAD

# File-by-file for large PRs
git diff main...HEAD -- src/file.py

# Quick checks
git diff main...HEAD | grep -n "TODO\|FIXME\|debugger\|print("
git diff main...HEAD | grep -in "password\|secret\|api_key"
```

### Review Checklist

- **Correctness**: Edge cases, error paths, concurrency
- **Security**: No hardcoded secrets, SQL injection, XSS
- **Code Quality**: Clear naming, DRY, single responsibility
- **Testing**: Happy path + error cases, readable tests
- **Performance**: N+1 queries, blocking operations in async code

### Review PR on GitHub

```bash
gh pr view 123
gh pr diff 123 --name-only
git fetch origin pull/123/head:pr-123 && git checkout pr-123
```

### Submit Formal Review

```bash
gh pr review 123 --approve --body "LGTM!"
gh pr review 123 --request-changes --body "See inline comments."
```

### Inline Comments

```bash
HEAD_SHA=$(gh pr view 123 --json headRefOid --jq '.headRefOid')
gh api repos/$OWNER/$REPO/pulls/123/comments \
  --method POST \
  -f body="Use parameterized queries." \
  -f path="src/auth.py" -f commit_id="$HEAD_SHA" -f line=45 -f side="RIGHT"
```

### Review Output Format

Use the template in `references/review-output-template.md` with severity icons:
- 🔴 Critical — must fix before merge
- ⚠️ Warning — should fix
- 💡 Suggestion — non-blocking improvement
- ✅ Looks Good — positive reinforcement

---

## 5. Authentication Reference

Full auth setup for first-time configuration. See `references/github-auth.md` for complete instructions.

### Auth Methods

| Method | Best For | Setup |
|--------|----------|-------|
| HTTPS + PAT | Most portable | Create token at github.com/settings/tokens |
| SSH Key | Private repos, reliability | `ssh-keygen -t ed25519`, add to GitHub settings |
| gh CLI | Interactive use | `gh auth login` |

### Troubleshooting

| Problem | Fix |
|---------|-----|
| Push asks for password | Use PAT as password, or switch to SSH |
| Permission denied | Token may lack `repo` scope |
| SSH connection refused | Try port 443: add `Host github.com Hostname ssh.github.com Port 443` to `~/.ssh/config` |

---

## Quick Reference Table

| Action | gh | curl endpoint |
|--------|-----|--------------|
| List repos | `gh repo list` | `GET /user/repos` |
| Clone | `gh repo clone o/r` | `git clone https://...` |
| Create repo | `gh repo create n --public` | `POST /user/repos` |
| List issues | `gh issue list` | `GET /repos/o/r/issues` |
| Create issue | `gh issue create ...` | `POST /repos/o/r/issues` |
| Create PR | `gh pr create ...` | `POST /repos/o/r/pulls` |
| Review PR | `gh pr review N ...` | `POST /repos/o/r/pulls/N/reviews` |
| Merge PR | `gh pr merge ...` | `PUT /repos/o/r/pulls/N/merge` |
| Check CI | `gh pr checks` | `GET /repos/o/r/commits/sha/status` |
| Re-run CI | `gh run rerun ID` | `POST /repos/o/r/actions/runs/ID/rerun` |
| Set secret | `gh secret set KEY` | `PUT /repos/o/r/actions/secrets/KEY` |
| Create release | `gh release create v1.0` | `POST /repos/o/r/releases` |

## References

| File | Content |
|------|---------|
| `references/github-auth.md` | Full auth setup (PAT, SSH, gh CLI) |
| `references/issues.md` | Complete issue management guide |
| `references/pr-workflow.md` | Full PR lifecycle (branch, CI, merge) |
| `references/code-review.md` | Code review checklist and procedures |
| `references/repo-management.md` | Repo ops (clone, create, fork, releases) |
| `references/conventional-commits.md` | Commit message format reference |
| `references/ci-troubleshooting.md` | CI failure diagnosis and fixes |
| `references/review-output-template.md` | PR review comment template |
| `references/github-api-cheatsheet.md` | Complete REST API endpoint reference |
| `references/git-filter-repo-cheatsheet.md` | Scrubbing secrets from git history |

## Templates

| File | Content |
|------|---------|
| `templates/bug-report.md` | Structured bug report |
| `templates/feature-request.md` | Feature request template |
| `templates/pr-body-feature.md` | PR description for features |
| `templates/pr-body-bugfix.md` | PR description for bug fixes |

## Scripts

| File | Content |
|------|---------|
| `scripts/gh-env.sh` | Auth detection + env vars helper |

## Common Pitfalls

1. **Auth boilerplate repeated** — use `scripts/gh-env.sh` instead of rewriting the detection block
2. **Token in URL fails for private repos** — use SSH: `git clone git@github.com:owner/repo.git`
3. **.gitignore after commit** — doesn't protect secrets already in history; use `git-filter-repo`
4. **filter-repo removes origin** — `git remote add origin <url>` after scrubbing
5. **Conventional commits** — use the correct type: `feat:`, `fix:`, `refactor:`, etc.
6. **`--dangerously-skip-permissions` dialog** — if using External AI coding agents, handle the "down + enter" dialog
