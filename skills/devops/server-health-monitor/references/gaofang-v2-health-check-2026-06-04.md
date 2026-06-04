# Gaofang V2 Health Check — 2026-06-04

## Session Context

- **Cron run**: 2026-06-04 07:03 +0800
- **Target**: http://39.107.78.58 (Aliyun ECS)
- **Project**: gaofang-v2-fusion (Flask + Gunicorn + Nginx)
- **IP**: 39.107.78.58 (Aliyun)
- **Result**: ✅ All OK — clean run, no anomalies

## Clean Run Profile (What "Normal" Looks Like)

This session documents a completely healthy server state. Use this as a baseline to compare against when anomalies appear.

### Services
- **gaofang-v2-fusion**: active ✅
- **nginx**: active ✅

### HTTP Endpoints
- **/nginx-health**: OK ✅
- **/**: HTTP 200 ✅

### Error Logs

**Nginx error log** (`/www/wwwlogs/gaofang-v2_error.log`):
- No entries on June 3 or June 4 (last errors from June 2 — 2 days prior)
- `grep -c "2026/06/0[34]"` returns 0

**Gunicorn error log** (`/workspace/projects/drug-distribution-system/gaofang-v2/logs/gunicorn-error.log`):
- 06:00 routine HUP reload: SIGHUP sent to 4 old workers → 6 new workers booted → old workers exited (SIGTERM + cleanup)
- Pattern: `[ERROR] Worker (pid:X) was sent SIGHUP!` → `[INFO] Booting worker...` → `[INFO] Handling signal: hup` → `[INFO] Hang up: Master` → `[INFO] Worker exiting` → `[ERROR] Worker (pid:Y) was sent SIGTERM!`
- **This is a normal reload** — the `[ERROR]` level on SIGHUP/SIGTERM messages is gunicorn's default, not actual errors
- Overnight: WARNING-level scanner probes from 8 different IPs — not flagged
- **No ERROR-level entries from the application itself**

### Database
- **PostgreSQL** (gaofang_v2, gaofang_app@localhost): SELECT 1 ✅ OK
- Connection method: project venv python (`venv38/bin/python` with psycopg2) + fallback password from `config.py`

### System Resources
- **Disk**: 66% used (25G / 40G, 13G free)
- **Uptime**: 2 days 9 hours (boot ~06-01 21:55)
- **Load**: 0.17 / 0.08 / 0.03

### Scanner IPs Seen (WARNING-level, not flagged)
| IP | Pattern | Count |
|---|---|---|
| 66.132.186.192 | HTTP/2 probe (Invalid Version: 2, 0) | 1 |
| 66.132.195.88 | HTTP/2 probe | 1 |
| 139.162.3.144 | Multi-protocol scanner (RTSP, TLS handshake, HELP cmd, nmap) | 4 |
| 176.120.22.240 | mstshash cookie probe | 2 |
| 178.159.37.70 | mstshash cookie probe | 2 |
| 79.124.59.86 | mstshash cookie probe | 2 |
| 88.214.25.123 | mstshash cookie probe | 1 |
| 111.7.96.150 | Empty request line probe | 1 |

### Path Discovery Notes
- Task description cited `~/wangzhaotong-hermes/drug-distribution-system/gaofang-v2/` (does not exist)
- wwwroot at `/www/wwwroot/gaofang-v2/` is a placeholder (index.html only)
- **Found via**: `systemctl cat gaofang-v2-fusion.service` → `WorkingDirectory=/workspace/projects/drug-distribution-system/gaofang-v2`
- Nginx logs at `/www/wwwlogs/gaofang-v2_error.log` — confirmed correct
