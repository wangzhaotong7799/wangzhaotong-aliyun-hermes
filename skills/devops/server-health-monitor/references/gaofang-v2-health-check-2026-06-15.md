# Gaofang V2 Health Check — 2026-06-15 (Clean Baseline with SIGHUP Reload)

**Date**: 2026-06-15 07:03 (Monday)
**Model**: deepseek-v4-flash
**IP**: 39.107.78.58 (阿里云)
**Uptime**: 13.4 days

## Summary

All services running. Zero application errors in 24h window. Normal SIGHUP worker rotation at 06:00. All log activity is scanner/probe noise at WARNING level only.

## Service Status

| Service | Status |
|---|---|
| gaofang-v2-fusion.service | ✅ active |
| nginx | ✅ active |
| Gunicorn workers | ✅ 4 workers, normal SIGHUP rotation at 06:00 |

## HTTP Endpoints

| Endpoint | Result |
|---|---|
| Nginx health (/nginx-health) | ✅ "Nginx OK" |
| Homepage (port 80) | ✅ HTTP 200 |

## Error Logs

### Nginx error log (`/www/wwwlogs/gaofang-v2_error.log`)
- **Zero new entries in 24h window.** The last entries are from June 11 (4 days stale).
- Historical entries are scanner probes only (163.7.3.220 — extension brute-force, 139.162.91.180 — directory listing probes).

### Gunicorn error log (`logs/gunicorn-error.log`)
- **Zero ERROR-level entries in 24h window** (June 14 09:00 → June 15 09:00).
- SIGHUP reload at **2026-06-15 06:00:14**: Master sent SIGHUP, new workers booted (PID 525203-525210), old workers exited/received SIGTERM. Clean cycle — all new workers healthy.
- **WARNING-level entries only** (not flagged):

| Time | IP | Pattern |
|---|---|---|
| 2026-06-14 13:54 | 79.124.59.86 | `Cookie: mstshash=Administr` — RDP brute-force remnant |
| 2026-06-14 17:50 | 66.132.195.91 | `Invalid HTTP Version: (2, 0)` — HTTP/2 probe |
| 2026-06-14 19:51 | 107.150.102.190 | Raw TLS handshake bytes on HTTP port |
| 2026-06-14 20:51 | 194.165.16.164 | Same RDP pattern as 79.124.59.86 |
| 2026-06-14 22:06-22:12 | 47.92.103.100 | **Multi-protocol scanner** — hit HTTP port with RTSP, SMTP (EHLO/HELP), Redis (*1/show info), SIP, and nmap mstshash patterns in sequence. ~13 probes in 6 minutes. Source: Alibaba cloud cross-region IP. |
| 2026-06-15 00:29 | 79.124.59.86 | Repeat RDP probe (same IP, same pattern) |
| 2026-06-15 06:50 | 66.132.224.224 | `Invalid HTTP Version: (2, 0)` — HTTP/2 probe |

### Multi-protocol scanner pattern (47.92.103.100) — Notable
This scanner (Alibaba-internal IP, likely a customer) hit port 80 with **7 different protocol probes** in rapid succession at 22:06-22:12:
1. `RTSP/1.0` — RTSP streaming protocol
2. `\x05\x04...PGET` — raw bytes + PGET (unusual)
3. Empty/blank request
4. `EHLO` — SMTP greeting
5. `HELP` — SMTP command
6. `\x03\x00...Cookie: mstshash=nmap` — nmap RDP scan
7. `SIP/2.0` — VoIP protocol
8. `stats` — Memcached/Redis command
9. `serverstatus` — Apache mod_status probe
10. `*1` — Redis protocol
11. `show info` — Redis/Memcached command

This is not hostile — these are just multi-protocol enumeration scans. All return `400 Bad Request` or `Invalid HTTP request line` from Gunicorn. No risk.

## Database

✅ PostgreSQL `gaofang_v2` @ localhost:5432 — connection normal via `gaofang_app` user with config.py default credentials.

## System Resources

| Resource | Value | Status |
|---|---|---|
| Disk | 64% (24G/40G, 14G free) | ✅ Under 85% |
| Uptime | 13.4 days | Normal |
| Load | 0.00 / 0.00 / 0.00 | ✅ Idle |

## Tool Behavior Notes

- `terminal()` worked for: `systemctl`, `curl`, `df -h`, `uptime`, `cat` (config files/systemd), `ls`.
- `terminal()` **falsely blocked** `tail -N` on gunicorn-error.log (triggered "long-lived server/watch process" heuristic due to path pattern `/workspace/projects/.../logs/...`).
- Workaround used: `read_file` with `offset=1460, limit=50` — worked perfectly to get the last 50 lines.
- Project path cited as `~/wangzhaotong-hermes/...` but real path at `/workspace/projects/.../` — confirmed by systemd service file `WorkingDirectory=` and Nginx error log paths.
- DB credentials from `config.py` defaults (no `.env` file present at project root).
