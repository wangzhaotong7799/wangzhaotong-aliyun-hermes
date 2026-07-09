---
name: linux-disk-hygiene
title: Linux Disk Hygiene
description: Systematic disk space audit, safe cleanup, and automated maintenance for Linux servers. Covers assessment, target identification, script-based cleanup, and cron-based scheduling.
trigger: user asks about disk cleanup, disk space, cleaning up the server, freeing space, or mentions / filling up
domain: devops
---

# Linux Disk Hygiene

Systematic approach to keeping a Linux server's disk clean — safely removing redundant files without touching active services, project files, or swap.

## Quick Assessment

```bash
# Overall usage
df -h /

# Biggest directories — probe known-large dirs individually to avoid timeout
du -sh /var/log /var/cache /tmp /root /www 2>/dev/null | sort -rh

# For /root/, check specific known space hogs:
du -sh /root/.cache /root/.npm /root/.local /root/hermes-backup* /root/.hermes.old* /root/.hermes.backup* 2>/dev/null | sort -rh

# Check journald size
journalctl --disk-usage 2>/dev/null
```

> ⚠️ **`du -sh /*` can time out** on servers with 4G+ of logs or large cache directories. Always probe individual directories instead of scanning `/` or `/root/*` in one pass. Use `df -h` first for the overview, then target specific directories.

## Safe Cleanup Targets (by safety level)

### ✅ Tier 1 — Always safe (no side effects)

| Target | Typical size | How to clean |
|--------|-------------|--------------|
| Hermes conversation exports (`/root/hermes_conversation_*.json`) | ~1-3 MB | `rm -f /root/hermes_conversation_*.json` |
| Old Hermes backup scripts (`hermes_main_backup_*.py`) | ~600 KB | `rm -f /root/hermes_main_backup_*.py` |
| Old env/config backups (`hermes_env_backup_*.txt`, `hermes_config_backup_*.yaml`) | ~50 KB | `rm -f /root/hermes_env_backup_*.txt /root/hermes_config_backup_*.yaml` |
| Redundant SQL dumps in `/root` (not in `/root/db_backups/`) | varies | Check if `/root/db_backups/` already has a copy via daily backup |
| BT install scripts (`install_panel.sh`) | ~80 KB | Safe to delete once panel is running |
| npm cache (`~/.npm`) | 50-200 MB | `npm cache clean --force` + `rm -rf ~/.npm/_cacache` |
| pip cache (`~/.cache/pip`) | 50-200 MB | Only clean if >50 MB: `rm -rf ~/.cache/pip/*` |
| `/tmp` old temp files | varies | `find /tmp -maxdepth 1 -type f -mtime +7 -delete` |

### ⚠️ Tier 2 — Check before cleaning

| Target | Why cautious |
|--------|-------------|
| `~/.cache/` (general) | May speed up rebuilds; check individual subdirs |
| Old kernel images (`/boot/vmlinuz-*`) | Needs `apt autoremove` or manual `dpkg --purge` |
| package manager cache (`/var/cache/apt/`, `/var/cache/yum/`) | Minor gain; `apt clean` / `yum clean all` |
| journal logs | `journalctl --disk-usage` then `journalctl --vacuum-time=7d` |
| `~/go/pkg/mod/` | Go module cache; safe if no active Go builds |

### 🚫 Tier 3 — NEVER touch

| Target | Why |
|--------|-----|
| `/www/server/` | BT panel files — **铁律第7条禁止修改** |
| Active swap files | Verify with `swapon --show` before any swap operation |
| Active project directories | `/root/wangzhaotong-hermes/`, `/root/projects/`, etc. |
| Daily backup dir | `/root/db_backups/` — active backup system |
| System directories | `/usr/`, `/etc/`, `/var/`, `/boot/` (without specific knowledge) |

## Common Pitfalls

1. **Don't delete files that look like "backup" but are actually active backups.** Always check: is there a cron/systemd timer for it? Is it part of a daily rotation? If yes, leave it.
2. **Swap files look big and idle but they're actively registered.** `swapon --show` tells you what's in use. Zero-used swap can still be needed under load.
3. npm cache can't be fully cleaned by `npm cache clean --force` alone. Follow up with `rm -rf ~/.npm/_cacache`.
4. **`du -sh /*` and broad `du` calls can time out on large filesystems.** On servers with 4G+ of logs or cached data, `du` traversing `/` or `/root/*` can hang for 30+ seconds and get killed by the tool timeout. **Workaround:** use the targeted probe commands in the Quick Assessment section above — check specific known-large directories instead of scanning all files in one pass.
5. **Always present the audit before deleting.** Per user preference: show the list first, get confirmation.

## Setting Up Automated Cleanup

### 1. Create the script

A reusable weekly cleanup script covers:
- Hermes conversation exports
- Old backup scripts / config backups
- Redundant SQL dumps outside the backup directory
- Install scripts
- npm / pip cache (if above threshold)
- Old temp files

Use the template at `templates/weekly-cleanup.sh` as a starting point — customize threshold values and target patterns per server.

### 2. Schedule via system crontab

```bash
# Add to user's crontab
(crontab -l 2>/dev/null; echo "30 6 * * 1 /path/to/cleanup.sh") | crontab -

# Verify
crontab -l | grep cleanup
```

### 3. Logging

The script should log to a dedicated log file with timestamps and summary. Keep the last N entries to avoid the log itself becoming a problem.

## Verification

After cleanup, verify with:
```bash
df -h /
echo "Space saved: check before/after"
```
