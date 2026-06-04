# Gaofang V2 Health Check — 2026-06-01

## Session Context
- Autonomous cron job, no user present
- **No tirith scanner blocks** this session — all `terminal()` commands worked directly (systemctl, curl, grep, df, uptime)
- Notable difference from 2026-05-28 session where everything was blocked — scanner may have been updated/disabled

## Key Findings

### 1. Gunicorn HUP reload at 06:04:50 (today)
Two reloads observed:
- **2026-05-30 06:00**: HUP reload → worker 1254301 exited cleanly (1s), worker 1254300 took 2min to timeout → `[CRITICAL] WORKER TIMEOUT` + `SIGKILL` + `Perhaps out of memory?` at 06:02:07
- **2026-06-01 06:04**: HUP reload → both old workers (1331052, 1331053) exited cleanly in ~2s. New workers (1375733-1375736) booted. Clean reload ✅

Pattern: SIGHUP at 06:00 daily (cron-managed restart). Workers that hold DB connections take longer to drain. The `SIGTERM` + `SIGKILL` + `Perhaps out of memory?` triad on May 30 is a normal slow-worker timeout artifact, NOT an OOM.

### 2. May 30 static file 404 errors
```
[2026-05-29 03:32] error: open() ".../static/css/app.css" failed (2: No such file or directory)
[2026-05-30 04:46] error: open() ".../static/lib/js/chart.js" failed (2: No such file or directory)
[2026-05-30 04:46] error: open() ".../static/js/r.js" failed (2: No such file or directory)
[2026-05-30 04:46] error: open() ".../static/js/XLSX.utils.js" failed (2: No such file or directory)
[2026-05-30 04:46] error: open() ".../static/js/response.js" failed (2: No such file or directory)
[2026-05-30 04:46] error: open() ".../static/lib/js/Chart.js" failed (2: No such file or directory)
[2026-05-30 04:46] error: open() ".../static/lib/js/xlsx.js" failed (2: No such file or directory)
```
- All from host `byw-841007.hichina.com` (different hostname, not the main domain)
- These are requests hitting this Nginx from a stale/misconfigured other domain's DNS
- NOT application errors — the other site has references to JS/CSS files that don't exist on this server
- All are 404-level (nginx can't find the file to serve), not upstream errors

### 3. terminal tool path-based false positive
`tail -30 /workspace/projects/drug-distribution-system/gaofang-v2/logs/gunicorn-error.log` was blocked by Hermes's foreground-server detection heuristic. Workaround: `read_file` with offset/limit worked perfectly.

### 4. Bot scan activity (24h window: May 31 09:00 — June 1 09:00)
Gunicorn WARNING-level entries (all from automated scanners):
| Timestamp | Source IP | Pattern |
|-----------|-----------|---------|
| 2026-05-31 13:59 | 79.124.59.86 | Invalid HTTP request line (malformed) |
| 2026-05-31 14:41 | 45.227.254.155 | Same pattern |
| 2026-05-31 14:56 | 79.124.59.86 | Same (persistent scanner) |
| 2026-05-31 17:14 | 66.132.186.171 | Invalid HTTP Version: (2, 0) |
| 2026-05-31 17:37 | 167.94.146.62 | Invalid HTTP Version: (2, 0) |
| 2026-05-31 20:47 | 192.253.248.180 | Malformed request |
| 2026-06-01 00:41 | 79.124.59.86 | Same (repeat offender) |
| 2026-06-01 01:22 | 93.123.109.72 | Malformed request |
| 2026-06-01 04:24 | 66.132.172.108 | Invalid HTTP Version: (2, 0) |
| 2026-06-01 04:34 | 192.253.248.180 | Malformed |
| 2026-06-01 04:38 | 79.124.59.86 | Same |

79.124.59.86 is the most active scanner — hits at multiple times daily. All WARNING level, no actual application impact.

Zero ERROR-level entries in the 24h window in both nginx and gunicorn error logs.

## All Check Results

| Check | Method | Result |
|-------|--------|--------|
| `systemctl is-active gaofang-v2-fusion.service` | raw `terminal` | ✅ "active" |
| `systemctl is-active nginx` | raw `terminal` | ✅ "active" |
| `curl http://127.0.0.1/nginx-health` | raw `terminal` | ✅ "Nginx OK" |
| `curl http://127.0.0.1/` | raw `terminal` | ✅ "HTTP 200" |
| `tail -50 /www/wwwlogs/gaofang-v2_error.log` | raw `terminal` | ✅ 50 lines, newest 05/30 (static file 404s from other host) |
| `grep -E "2026/0(5/31|6/01)"` on error log | raw `terminal` | ✅ 0 entries — no errors in 24h window |
| venv python psycopg2 connect | raw `terminal` | ✅ 连接正常 |
| `df -h /` | raw `terminal` | ✅ 23G/40G (62%) |
| `uptime -p` | raw `terminal` | ✅ 5 weeks 4 days 20 hours |

## Project Layout (Confirmed — unchanged)

| Path | Content |
|------|---------|
| `/workspace/projects/drug-distribution-system/gaofang-v2/` | Real project (service WorkingDirectory) |
| `/etc/systemd/system/gaofang-v2-fusion.service` | systemd unit — Gunicorn via venv38 |
| `/www/wwwlogs/gaofang-v2_error.log` | Nginx error log |
| `/workspace/.../logs/gunicorn-error.log` | Gunicorn error log (1066 lines, 104KB) |
| `/workspace/.../logs/gunicorn-access.log` | Gunicorn access log (3.8MB, last modified 06:46 today) |

## Nginx proxy temp Permission Denied (still unfixed)
- Last occurrence: 2026-05-12 (4 `crit` entries) — 20 days ago
- No recurrence — latent risk, unfixed
