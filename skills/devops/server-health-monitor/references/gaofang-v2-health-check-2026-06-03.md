# Gaofang V2 Health Check — 2026-06-03

## Session Context

- **Cron run**: 2026-06-03 07:36 +0800
- **Target**: http://39.107.78.58 (Aliyun ECS)
- **Project**: gaofang-v2-fusion (Flask + Gunicorn + Nginx)
- **Cloud**: Aliyun ECS (39.107.78.58)

## Key Findings

### 1. Upstream Timeouts — Genuine Slow Queries (NOT restart artifacts)

7 upstream timeouts on 2026-06-02 between 15:24 and 15:30:

| Time | Endpoint | Client IP |
|------|----------|-----------|
| 15:24:54 | `/api/prescriptions?status=欠药&patient_name=CLY&page=1&page_size=50` | 1.62.185.204 |
| 15:25:04 | `/api/assistants?start_date=2025-12-02` | 1.62.185.204 |
| 15:25:11 | `/api/prescriptions?status=欠药&patient_name=CL&page=4&page_size=50` | 1.62.185.204 |
| 15:25:48 | `/api/prescriptions?status=欠药&patient_name=CL&page=4&page_size=50` | 1.62.185.204 |
| 15:26:34 | `/api/prescriptions?status=欠药&patient_name=SGX&page=1&page_size=50` | 1.62.185.204 |
| 15:28:42 | `/api/prescriptions?status=未取&page=1&page_size=50` | 1.62.185.204 |
| 15:30:28 | `/api/prescriptions?status=未取&patient_name=NFL&page=2&page_size=50` | 1.62.185.204 |

**Pattern**: All from the same client IP (1.62.185.204), hitting paginated prescription search endpoints with patient name filters. Gunicorn's `--timeout 120` was exceeded, causing nginx to timeout first (default proxy_read_timeout 60s).

**Key distinction from restart artifacts**: The last gunicorn restart (SIGHUP) was at 06:00 — over **9 hours before** these timeouts. No correlation in time. This is a genuine slow-query pattern, not restart-induced.

**Root cause hypothesis**: Prescription search queries with `LIKE '%keyword%'` on `patient_name` are not indexed, causing sequential scans large enough to exceed the 60s proxy timeout for certain name patterns.

**Signal to look for in future**: Timeouts clustered on specific API endpoints with database-backed queries, from the same client IP, with no nearby restart signal → slow queries.

### 2. Nginx client_body Permission Denied (3 occurrences)

| Time | Error |
|------|-------|
| 16:29:56 | `open() "/var/lib/nginx/tmp/client_body/0000000001" failed (13: Permission denied)` |
| 16:30:01 | `open() "/var/lib/nginx/tmp/client_body/0000000002" failed (13: Permission denied)` |
| 16:31:00 | `open() "/var/lib/nginx/tmp/client_body/0000000003" failed (13: Permission denied)` |

**All three** were on `POST /api/import` from the same client IP (1.62.185.204).

**Directory permissions at time of check** (next day):
```
/var/lib/nginx/tmp/          -> drwxrwx--x  nginx:root  (771)
/var/lib/nginx/tmp/client_body/ -> drwx------  www:root   (700)
```

Nginx workers run as `www` user (confirmed by `ps aux | grep nginx` and `grep '^user ' /etc/nginx/nginx.conf`).

**Puzzle**: `www` owns the `client_body` dir (`700`), so write should succeed. But the errors show `Permission denied`. Possible explanations:
- The directory didn't exist at 16:29 — nginx tried to create it but parent `tmp/` (owned by `nginx:root`, 771) didn't allow `www` to create subdirs. The `client_body/` dir we saw at 07:36 the next day was created by the `root` user (maybe a reboot or manual fix).
- Transient race condition on tmp file creation under concurrent imports.
- SELinux / AppArmor interference (not verified).

**Resolution**: After the errors, the last modified time of `client_body/` was 16:36 (5 minutes after the last error), suggesting something fixed the directory structure. No recurrences the following day.

## Uptime
- Server boot: 2026-06-01 21:55
- Uptime at check: ~1 day 11 hours

## Disk
- 25G / 40G used (66%) — healthy
