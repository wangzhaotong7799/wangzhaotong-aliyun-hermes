# Gaofang V2 Health Check — 2026-06-09

## Session Context

- **Cron run**: 2026-06-09 07:13 +0800
- **Target**: http://39.107.78.58 (Aliyun ECS)
- **Project**: gaofang-v2-fusion (Flask + Gunicorn + Nginx)
- **Result**: ✅ All OK — clean run, no anomalies

## Clean Run Profile

### Services
- **gaofang-v2-fusion**: active ✅
- **nginx**: active ✅

### HTTP Endpoints
- **/nginx-health**: "Nginx OK" ✅
- **/**: HTTP 200 ✅

### Error Logs

**Nginx error log** (`/www/wwwlogs/gaofang-v2_error.log`):
- **Last entry**: 2026-06-07 04:12 (2 days prior)
- **No entries on June 8 or June 9** — zero new errors in 24h window
- Historical entries still present: June 2 upstream timeouts, June 5/6/7 bot scanning 404s

> ⚠️ **Key diagnostic observation**: Nginx error log had been silent for 2 days, but the **app.log was still actively logging** (June 9 entries). When the Nginx error log appears stale, always check app.log separately — Nginx only records proxy-level errors (timeouts, connection refused, file-not-found), while app.log captures every request including bot traffic. A quiet Nginx error log does NOT mean the server is idle.

**App log** (`/workspace/projects/drug-distribution-system/gaofang-v2/app.log`):
- Active traffic on June 9 (bot probes, 404s only)
- **Zero ERROR/CRITICAL/Traceback/Exception** entries in the entire log history
- All entries are WARNING-level 404 responses to scanner probes

### Database
- **PostgreSQL** (gaofang_v2, gaofang_app@localhost:5432): SELECT 1 = ✅
- Connection method: `source .env; python3 -c "import psycopg2; ..."` — note: `.env` password is masked as `***` in both `read_file` and `cat` output, but `source .env` expands it correctly for the Python command

### System Resources
- **Disk**: 61% used (23G / 40G, 15G free)
- **Uptime**: 7 days 9 hours
- **Load**: 0.07 / 0.08 / 0.02 (very low)

### Bot Scanner Activity — App.log 404 Warnings (June 9, first 7h)

| Timestamp (June 9) | Path | Pattern Type |
|---|---|---|
| 03:57 | `/favicon.ico`, `/robots.txt`, `/sitemap.xml`, `/config.json` | Standard crawler batch |
| 04:24 | `/portal/redlion` | Red Lion SCADA / CVE probe |
| 04:57–05:31 | `/favicon.ico`, `/security.txt`, `/robots.txt`, `/sitemap.xml`, `/config.json` | Standard crawler (second batch) |
| 05:28, 06:38, 06:42 | `/SDK/webLanguage` | **ZTE/LTE gateway vulnerability probe** (repeated, from possibly different IPs) |
| 05:49 | `/video.dispatch.tc.qq.com/...` (mp4 path) | Tencent video endpoint hallucination — bot crafting URLs with QQ video paths |
| 05:51 | `/login` | General login page probe |
| 06:05 | `/boaform/admin/formLogin` | **ZTE router / CVE-2015-6967 class exploit probe** |
| 06:43 | `/zc` | Unknown short-path probe |

#### Notable Patterns (Document for Future Reference)

1. **ZTE/LTE Gateway probes**: `/SDK/webLanguage`, `/boaform/admin/formLogin` — these target Chinese-manufactured LTE routers (often CVE-2015-6967 or similar class). Multiple hits from this probe type suggest a dedicated scanner targeting Chinese-hosted servers. If hundreds per day, consider blocking at firewall.

2. **Standard crawler batches**: The 03:57 and 05:31 batches (favicon → robots → sitemap → config) are likely SEO/scraper bots, not vulnerability scanners. Low volume, ignore.

3. **Tencent video path hallucination**: `/video.dispatch.tc.qq.com/...` is a bogus URL that some scanner is constructing by prepending the site origin to a full Tencent CDN URL. Harmless, but distinctive.

### Project Path Discovery

- Task cited `~/wangzhaotong-hermes/drug-distribution-system/gaofang-v2/` — **does not exist**
- Found via `find / -name "gaofang*" -type d 2>/dev/null` → `/workspace/projects/drug-distribution-system/gaofang-v2/`
- wwwroot at `/www/wwwroot/gaofang-v2/` exists but is a separate deployed copy
- `.env` is at the workspace path, not wwwroot
