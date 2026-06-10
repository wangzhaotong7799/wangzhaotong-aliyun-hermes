# Gaofang V2 Health Check — 2026-06-10

## Session Context

- **Cron run**: 2026-06-10 09:00 +0800
- **Target**: http://39.107.78.58 (Aliyun ECS)
- **Project**: gaofang-v2-fusion (Flask + Gunicorn + Nginx)
- **Result**: ✅ All OK — clean run, no anomalies

## Clean Run Profile

### Services
- **gaofang-v2-fusion**: active ✅
- **nginx**: active ✅

### HTTP Endpoints
- **/nginx-health**: HTTP 200 ✅
- **/**: HTTP 200 ✅

### Error Logs

**Nginx error log** (`/www/wwwlogs/gaofang-v2_error.log`):
- **122 new entries on June 10** (all from 03:05–03:11 UTC, i.e., 11:05–11:11 CST)
- **All 122 are from a single IP**: 163.7.3.220
- **All 122 are `open() ... failed (2: No such file or directory)`** — 404 scanner noise
- **Zero application-level errors** (no 500/502/504, no Python tracebacks, no database errors)

### Static File Extension Brute-Force Scanner (163.7.3.220) — Detailed Pattern

**Source IP**: 163.7.3.220
**Volume**: 122 requests in ~6 minutes (03:05–03:11 UTC)
**Error type**: Nginx 404 — `open() \".../static/...\" failed (2: No such file or directory)`

**Files targeted and extension sequence observed:**

| Base File | Extensions Tried |
|---|---|
| `chart` (in `/static/lib/js/`) | `.txt`, `.yaml`, `.yml`, `.conf`, `.bak`, `.old`, `.env` |
| `xlsx.full.min.js` (in `/static/lib/js/`) | `.map`, `.js`, `.json`, `.php`, `.txt`, `.yaml`, `.yml`, `.conf`, `.bak`, `.old`, `.env` |
| `common.js` (in `/static/js/`) | `.map`, `.js`, `.json`, `.php`, `.txt`, `.yaml`, `.yml`, `.conf`, `.bak`, `.old`, `.env` |
| `page-` (in `/static/js/`) | `(empty)`, `.js`, `.json`, `.php`, `.txt`, `.yaml`, `.yml`, `.conf`, `.bak`, `.old` |
| `page-prescriptions.js` (in `/static/js/`) | `.map`, `.js`, `.json`, `.php`, `.txt`, `.yaml`, `.yml`, `.conf`, `.bak`, `.old`, `.env` |

**Extension order tried per file**: `.ext` → `.js` → `.json` → `.php` → `.txt` → `.yaml` → `.yml` → `.conf` → `.bak` → `.old` → `.env`

**Behavior pattern**: The scanner first discovers a real static file through normal page loading (e.g., `chart` from a JS import), then systematically probes every common extension variation to find misconfigured or backup files. The `.js` → `.js.js`, `.js.json`, `.js.php`, etc. pattern suggests it's adding extensions on top of existing JS paths.

**Diagnostic value**: This scanner is **harmless** but produces enough noise to obscure real errors if viewing raw logs. When counting errors for the daily report:
- Filter *out* `open() ... failed (2: No such file or directory)` from error counts
- Only count ERROR-level entries from the application itself (500/502/504, Python tracebacks, database connection failures)
- If the volume is very high (>200/day from same IP), annotate the report with a note about potential Nginx-level IP blocking

### Database
- **PostgreSQL** (gaofang_v2, gaofang_app@localhost:5432): ✅ SELECT 1 = OK
- Connection method: Direct `psycopg2.connect()` using default credentials from `config.py` (`password='gaofang_password'`)

### System Resources
- **Disk**: 62% used (23G / 40G, 15G free) — healthy
- **Uptime**: 8 days
- **Load**: Normal (low-traffic)

### Project Path Discovery

- Task cited `~/wangzhaotong-hermes/drug-distribution-system/gaofang-v2/` — **does not exist**
- Real project root: `/workspace/projects/drug-distribution-system/gaofang-v2/`
- Nginx error log confirms: paths in error logs reference `/workspace/projects/.../gaofang-v2/`
- **Always check Nginx error log paths first** when the stated project path doesn't exist — logs reveal the real deployment location

### Scanner IP 163.7.3.220 — For Future Reference

If this IP appears again in subsequent health checks:
- It's a dedicated static file extension brute-forcer, not a general-purpose scanner
- Consistent timing: hits between 03:00–04:00 UTC (11:00–12:00 CST) in this observation
- Extends `.js` paths with common config/backup extensions systematically
- No evidence of SQL injection, path traversal, or other targeted attacks — purely file enumeration
