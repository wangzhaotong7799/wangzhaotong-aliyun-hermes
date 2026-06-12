# Gaofang V2 Health Check — 2026-06-12 07:03

**State: CLEAN**

## Summary
All services healthy. Scheduled SIGHUP reload at 06:00:55 completed smoothly.

## Service Status
- gaofang-v2-fusion: active ✅
- Nginx: active ✅

## HTTP Endpoints
- `/nginx-health`: HTTP 200 ✅
- Homepage `/`: HTTP 200 ✅

## Error Logs
### Nginx (`gaofang-v2_error.log`)
- **4 errors** from 2026-06-11 15:35 (only entries in 24h window)
- All from IP **139.162.91.180** — scanner probing:
  - `/static/lib/js/bottom` — 404
  - `/static/chunks/` — directory listing forbidden
  - `/static/lib/js/chart.js` — 404
- No errors from 2026-06-12
- Previous entries all from 2026-06-07 and 2026-06-10 (old scanner bursts)

### Gunicorn (`gunicorn-error.log`)
- 5 WARNINGs from scanner IPs (80.66.88.40, 66.132.172.180, 79.124.59.86, 47.92.241.8, 66.132.195.61, 194.165.16.165) — invalid HTTP requests
- **SIGHUP reload at 06:00:55**: Workers sent SIGHUP → 8 new workers booted (409486-409493) → old workers exited cleanly
  - Old workers (371205-371208) logged `[ERROR] Worker was sent SIGHUP!` at 06:00:55 (standard logging, not an actual error)
  - Exit time: ~3 seconds (06:00:55→06:00:58)
- No application-level errors

## Database
- Connection: OK ✅ (gaofang_app@localhost:5432/gaofang_v2)

## System
- Disk: 63% (15G/40G) ✅
- Uptime: 1 week 3 days 9 hours

## Scanner Notes
- **139.162.91.180**: New scanner IP observed hitting `/static/chunks/` directory and `/static/lib/js/bottom` — different pattern from the extension brute-force type. Single request per path, not a burst.
- Standard scanner WARNINGs continue from multiple IPs. None warrant action.
