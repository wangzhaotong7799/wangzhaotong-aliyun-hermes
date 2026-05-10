# Cleanup Session — 2026-05-06

## Context
User asked to check V2 daily backup → discovered it's working → user requested full disk cleanup → then asked to automate weekly.

## Disk State Before
- 40G disk, 16G used (41%)
- 3 active swap files: /www/swap (1G), /www/swap2 (2G), /swapfile (3G) — all in use
- /www: 4.2G (2.1G swap2 + 1.1G swap + 1.2G server)

## Cleaned (Tier 1 — always safe)
- 7 old Hermes conversation exports (~2.2 MB)
- 2 old backup scripts (hermes_main_backup_*.py) + 2 old config backups (~670 KB)
- Redundant SQL dump (gaofang_v2_backup_20260505.sql — 1.2 MB; daily backup already had it)
- BT install script (install_panel.sh — 80 KB)
- npm cache (109 MB → 4 KB)

## Kept (Tier 3 — never touch)
- /root/db_backups/ — daily pg_dump rotation
- /root/wangzhaotong-hermes/ — config repo (removed only hermes-agent-source/ subdir, -66 MB)
- All swap files — actively registered
- /www/server/ — BT panel files (铁律禁止)

## Result
16G → 15G used. ~1 GB freed.

## Automation Created
- Script: /root/scripts/weekly_cleanup.sh
- Schedule: Mon 06:30 via system crontab
- Log: /root/scripts/weekly_cleanup.log
- Precedence: after 3 weekly reports (05:00/05:30/06:00)
