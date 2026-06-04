# Skill Backup to GitHub Repository

Reusable procedure for syncing recently-modified skills from `~/.hermes/skills/` to a GitHub backup repo and pushing.

This complements the pre-upgrade backup (`pre-upgrade-backup.md`) — which backs up everything before `hermes update`. This doc covers **routine daily/weekly skill backups** to a dedicated GitHub repo.

## Workflow

### 1. Find Recently Modified Skills

```bash
# Last 24 hours (use '-mmin -1440')
find ~/.hermes/skills -name "SKILL.md" -mmin -1440 2>/dev/null | sort

# Since a specific time (e.g., last night after 6pm)
find ~/.hermes/skills -name "SKILL.md" -newermt "2026-05-15 18:00" 2>/dev/null | sort

# All files modified in a skill directory (not just SKILL.md)
find ~/.hermes/skills -type f -newermt "YYYY-MM-DD HH:MM" 2>/dev/null | sort
```

### 2. Sync Skills to Repo

```bash
cd /path/to/repo

# Option A: rsync (preferred, handles deletions)
rsync -a --delete ~/.hermes/skills/<category>/<skill>/ ./skills/<category>/<skill>/

# Option B: cp (if rsync not available)
mkdir -p ./skills/<category>/<skill>
cp -r ~/.hermes/skills/<category>/<skill>/* ./skills/<category>/<skill>/

# Bulk: loop over a list of skills
for skill in category/skill-a category/skill-b; do
  src="$HOME/.hermes/skills/$skill"
  dst="/path/to/repo/skills/$skill"
  if [ -d "$src" ]; then
    mkdir -p "$dst"
    cp -r "$src/"* "$dst/"
    echo "✓ Synced: $skill"
  fi
done
```

⚠️ **Pitfall: rsync not installed** — On minimal Linux VMs (AlmaLinux, CentOS), rsync may be missing. Install with `yum install -y rsync` or fall back to `cp`.

### 3. Stage and Commit Selectively

```bash
cd /path/to/repo
git status --short   # Review what changed

# Stage all skill changes
git add skills/

# Stage project text files only (skip large binaries)
git add project-dir/scripts/*.py project-dir/docs/*.md project-dir/stories/*.txt

# NEVER git add -A when there are large media files (images, audio, video)
# It will hang or timeout. Always be selective.
```

⚠️ **Pitfall: `git add -A` times out** — If the repo has large untracked binaries (`.mp4`, `.jpg`, `.wav`, `.zip`), `git add -A` will take forever and likely timeout. Always stage specific directories/files.

```bash
git commit -m "🎯 Backup YYYY-MM-DD : Summary of changes"

git log -1 --oneline   # Verify commit
git push origin main
```

### 4. Verify

```bash
# Check push succeeded
git log -3 --oneline

# Confirm clean state (only intentionally-untracked files remain)
git status --short
```

## Common Patterns

| Pattern | Command |
|---------|---------|
| Find skills modified after specific time | `find ~/.hermes/skills -name "SKILL.md" -newermt "YYYY-MM-DD HH:MM"` |
| Find ALL files in skill dirs changed after time | `find ~/.hermes/skills -type f -newermt "YYYY-MM-DD HH:MM"` |
| Sync one skill directory | `rsync -a --delete ~/.hermes/skills/cat/skill/ ./skills/cat/skill/` |
| Stage specific text files only | `git add skills/ scripts/ docs/*.md` |
| Selective staging from horror-pipeline | `git add hp/scripts/*.py hp/docs/*.md hp/stories/*.txt hp/business_plan.md` |

## What NOT to Backup to Git

Large binary/media files that bloat the repo:
- `*.mp4`, `*.wav`, `*.mp3`, `*.jpg`, `*.png` (AI-generated media)
- `*.zip`, `*.tar.gz` (font archives, downloads)
- `__pycache__/` directories
- `.qkdownloading` files (partial downloads)

These belong on external storage or the repo's release assets, not in the git tree.

## Pitfall Summary

| Pitfall | Symptom | Fix |
|---------|---------|-----|
| rsync not installed | `Command not found` | `yum install -y rsync` or use `cp` |
| `git add -A` hangs | Command timed out after Ns | Stage specific paths, not everything |
| Large binary in commit | Repo becomes 100s MB | Add to `.gitignore`, then `git rm --cached` |
| Commit format inconsistent | Hard to track changes in log | Use the `🎯 Backup YYYY-MM-DD : summary` format |
