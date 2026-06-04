# Pre-Upgrade Backup Procedure

> Systematic backup before running `hermes update`. Run this before any Hermes Agent version upgrade.

## Overview

This procedure ensures safe Hermes Agent upgrades with:
- Full local tarball backup of config + runtime data + skills + source
- Secret-leak check (no API keys or tokens committed to GitHub)
- GitHub sync of all tracked config and skills

**Estimated time**: 2-5 minutes  
**Destructive operations**: None (read-only copy + push)

---

## Step-by-Step

### 1. Check Current Version

```bash
hermes --version
```

Record the version for rollback reference.

### 2. Create Local Backup (Timestamped)

```bash
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/root/hermes-backup-$TIMESTAMP"
mkdir -p "$BACKUP_DIR"
```

Backup these categories:

| Category | Path | Why |
|----------|------|-----|
| Config | `~/.hermes/config.yaml`, `.env`, `auth.json`, `SOUL.md`, `channel_directory.json`, `.gitignore`, `README.md` | Versioned settings |
| Runtime DBs | `~/.hermes/kanban.db`, `memory_store.db*`, `state.db*`, `response_store.db*` | Tasks, memory, session state |
| Skills | `~/.hermes/skills/` | All custom skills |
| Source | `~/.hermes/hermes-agent/` | Current codebase |
| Config dir | `~/.hermes/hermes_config/` | Platform configs |
| Memory | `~/.hermes/memory/`, `~/.hermes/memories/` | Long-term memory |
| Cron jobs | `~/.hermes/cron/` | Scheduled tasks |
| Checkpoints | `~/.hermes/checkpoints/` | Rollback snapshots |

```bash
cp -r ~/.hermes/config.yaml "$BACKUP_DIR/"
cp -r ~/.hermes/.env "$BACKUP_DIR/"
cp -r ~/.hermes/auth.json "$BACKUP_DIR/"
# ... continue for each category above
```

Verify: `du -sh "$BACKUP_DIR" && find "$BACKUP_DIR" -type f | wc -l`

### 3. Audit for Secret Leaks

Check `.gitignore` excludes these before pushing:

```bash
# Required exclusions
.env
.env.backup
auth.json
*.backup
state.db*
kanban.db
logs/
cache/
__pycache__/
```

Verify staged diff contains no secrets:

```bash
cd /path/to/repo
git diff --cached -- skills/ | grep -i "api_key\|secret\|token\|password" | head -5
# Should be empty (or only doc references, not actual values)
```

### 4. Sync Skills to GitHub Repo

```bash
cd /path/to/repo
rm -rf skills/
cp -r ~/.hermes/skills ./skills
rm -rf skills/.archive skills/.bundled_manifest skills/.curator_state skills/.hub
find skills/ -name '__pycache__' -type d -exec rm -rf {} +
find skills/ -name '*.pyc' -delete
cp ~/.hermes/config.yaml ./
cp ~/.hermes/SOUL.md ./
# ... other config files
```

### 5. Commit and Push

```bash
git add -A
git commit -m "🎯 升级前备份 $(date +%Y%m%d_%H%M): 全量技能同步 + 配置更新"
git push origin main
```

### 6. Verify Push

```bash
git log --oneline -1
# Should show the new commit on origin/main
```

---

## Rollback Procedure

If the upgrade fails and you need to restore:

```bash
# Option A: Restore from local backup
cp -r /root/hermes-backup-$TIMESTAMP/* ~/.hermes/

# Option B: Restore from GitHub
cd /path/to/repo
git checkout main
cp -r skills/* ~/.hermes/skills/
cp config.yaml ~/.hermes/config.yaml
# ... etc
```

---

## Pitfalls

- **`rsync` may not be installed** — use `cp -r` + `rm -rf` instead
- **`data/` directories under skills** may contain large report files (.docx, .md). They're useful for backup but consider if they should be in git (`.gitignore` optional per user)
- **Run `hermes doctor --fix` after restore** to re-link any paths or virtualenvs
- **Never push `.env` or `auth.json`** — even to private repos. If accidentally committed, rotate the keys immediately.
