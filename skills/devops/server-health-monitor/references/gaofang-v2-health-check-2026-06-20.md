# Gaofang V2 Health Check · 2026-06-20

## Summary: ✅ Clean run

All services healthy, no application errors. Nginx error log showed 16 entries from a new scanner type.

## Services
- gaofang-v2-fusion: active
- Nginx: active
- PostgreSQL: active, connection OK (password `gaofang_password` from config.py default)

## HTTP Endpoints
- `/nginx-health`: "Nginx OK"
- `/` (homepage): HTTP 200

## Error Logs

### Nginx error log (24h window): 16 entries
All from IP `172.104.140.44` — **Chart.js module enumeration scanner** (new variant, June 2026).

**Probe pattern:** Unlike the extension brute-force scanner (163.7.3.220, June 10), this scanner targets Chart.js-specific internals:
- **`.map` file probes**: `chart.umd.min.js.map`
- **Hex color paths** (Chart.js module names in hex): `cd853f`, `cd5c5c`, `db7093`
- **Chart.js component paths**: `/static/lib/js/bottom`, `/static/lib/js/bottomRight`, `/static/lib/js/bottomLeft`, `/static/lib/js/circle`, `/static/lib/js/circumference`, `/static/lib/js/tooltip`, `/static/lib/js/logarithmic`, `/static/lib/js/test`
- **Directory listing probes**: `/static/chunks/`, `/static/js/admin`, `/static/js/status`, `/static/js/application/json`

**Verdict:** Targeted scanner probing for Chart.js frontend internals. All return 404. Harmless.

### Gunicorn error log: Normal reload only
- 06:00:00 — SIGHUP reload (4 workers rebooted), all workers exited gracefully within 4 seconds
- 06:00:40 — `Invalid HTTP Version: (2, 0)` from IP `199.45.155.91` (standard HTTP/2 probe)

No application-level errors.

## Database
- PostgreSQL active, psycopg2 connection using `gaofang_app`/`gaofang_password` on `localhost:5432/gaofang_v2` → OK ✓

## System
- Disk: 66% (25G / 40G)
- Uptime: 18 days

## Notable
- First observation of Chart.js-specific module enumeration scanner (`172.104.140.44`). Unlike documented extension brute-force (163.7.3.220) and multi-protocol enumeration (47.92.103.100), this scanner knows Chart.js internals and probes for specific plugin/module paths in hex color notation. New variant for pitfall 6 documentation.
