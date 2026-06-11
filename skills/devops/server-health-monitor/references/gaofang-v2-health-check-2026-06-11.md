# Gaofang V2 Health Check — 2026-06-11

**Type**: Clean baseline with max-requests worker cycling

## Summary

All services healthy, zero application errors, clean worker rotation at 06:00.

## Services
| Service | Status | Details |
|---------|--------|---------|
| gaofang-v2-fusion | ✅ active | Gunicorn on :8080, 4 workers |
| Nginx | ✅ active | Reverse proxy on :80 |

## HTTP Endpoints
| Endpoint | Status |
|----------|--------|
| `/nginx-health` | ✅ "Nginx OK" |
| `/` (homepage) | ✅ HTTP 200 |

## Error Logs

### Nginx error log (`/www/wwwlogs/gaofang-v2_error.log`)
- **Today (06/11): 0 entries** — clean
- **Yesterday (06/10): 122 errors** — all from IP 163.7.3.220, static file extension brute-force scanner (see skill Pitfall 6). Not application errors.

### Gunicorn error log
- **06:00:00 — max-requests worker cycle** (max-requests=1000, max-requests-jitter=200)
- Sequence: 4 new workers boot → 4 old workers exit → `[ERROR] Worker (pid:X) was sent SIGTERM!` (4x) logged at ERROR level
- Old workers took ~3-4 seconds to drain → no SIGKILL/CRITICAL needed
- **No actual application errors**

### App log (`app.log`)
- **Today's WARNING entries (all scanner probes, none harmful)**:
  - `404错误: /../../../../../../etc/passwd` — path traversal probe
  - `404错误: /v1/models`, `/v1/embeddings`, `/v1/completions` — OpenAI API endpoint scanner
  - `404错误: /favicon.ico` — standard browser noise
- **No ERROR-level entries**

### Gunicorn access log
- Actively writing (confirmed via mtime)

## Database
| Check | Result |
|-------|--------|
| PostgreSQL connection | ✅ `SELECT 1` returned OK |

## System Resources
| Metric | Value |
|--------|-------|
| Disk usage | 62% (23G / 40G) |
| Root partition | `/dev/vda3` (ext4) |
| System uptime | 9 days |

## Key Observations
1. **First observed max-requests cycle** — confirms `max-requests=1000` is working. Old workers drained in ~3-4s (fast cleanup, no SIGKILL needed).
2. **Scanner IP 163.7.3.220 continues daily** — same static file extension brute-force scanner seen since 06/10. Volume: ~122 hits/day.
3. **New scanner patterns appeared** — path traversal and OpenAI API probes. These hit the Flask app (not Nginx static), so they appear in app.log, not nginx error log.
4. **read_file blocked on .env** as expected — config.py fallback password worked for DB test.
