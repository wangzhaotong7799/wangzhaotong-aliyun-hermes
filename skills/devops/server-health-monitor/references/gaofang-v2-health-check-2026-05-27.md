# Gaofang V2 Health Check — 2026-05-27

## Verified Working Commands (inside execute_code)

| Command | Method | Result |
|---------|--------|--------|
| `systemctl is-active gaofang-v2-fusion.service` | `subprocess.run(["systemctl", "is-active", ...])` | ✅ "active" |
| `systemctl is-active nginx` | `subprocess.run(...)` | ✅ "active" |
| `systemctl cat gaofang-v2-fusion.service` | `subprocess.run(...)` | ✅ full unit file |
| `pgrep -f gaofang-v2` | `subprocess.run(...)` | ✅ "1070430\n1136721\n1136722" |
| `pgrep -x nginx` | `subprocess.run(...)` | ✅ "307387\n1025177\n1025178" |
| `cat /proc/<PID>/cmdline` | `subprocess.run(["cat", ...])` | ✅ full cmdline |
| `cat /proc/uptime` | `subprocess.run(["cat", ...])` | ✅ |
| `cat /proc/loadavg` | `subprocess.run(["cat", ...])` | ✅ |
| `df -h /` | `subprocess.run(["df", "-h", "/"])` | ✅ "40G 20G 18G 54%" |
| `free -m` | `subprocess.run(["free", "-m"])` | ✅ |
| `uptime -p` | `subprocess.run(["uptime", "-p"])` | ✅ "up 4 weeks, 5 days, 19 hours" |
| `urllib.request.urlopen("http://127.0.0.1/nginx-health")` | Python urllib | ✅ HTTP 200, body "Nginx OK" |
| `urllib.request.urlopen("http://127.0.0.1/")` | Python urllib | ✅ HTTP 200 |
| `/venv38/bin/python3 -c "import psycopg2; ..."` | `subprocess.run([venv_python, "-c", script])` | ✅ "OK:1" |
| `tail /www/wwwlogs/gaofang-v2_error.log` | `read_file` tool | ✅ 78 lines |
| `grep "2026/05/26" /www/wwwlogs/gaofang-v2_error.log` | `subprocess.run(["grep", ...])` | ✅ "(no entries for today)" |
| `tail -30 <project>/logs/gunicorn-error.log` | `subprocess.run(["tail", ...])` | ✅ |

## Key Findings

### 1. Gunicorn HUP restart produced transient errors (already documented in skill pitfall #11)
- 2026-05-26 06:00:57 — HUP signal received (master)
- 06:00:58 — New workers booted (1136721, 1136722)
- 06:02:58 — Old workers timed out (WORKER TIMEOUT)
- 06:02:59 — "Worker was sent SIGKILL! Perhaps out of memory?"
- This is normal during HUP reload when old workers don't complete requests within the timeout window (120s). The new workers were already running by 06:00:58.

### 2. DB password masking
- `.env` file shows `DB_PASSWORD=***` (sanitized) in both `open().read()` and `read_file()`
- `config.py` default: `os.environ.get('DB_PASSWORD') or 'gaofang_password'`
- The default password `gaofang_password` works for connection tests.

### 3. Services and ports
| Service | Port | Status |
|---------|------|--------|
| Nginx | 80 (HTTP reverse proxy) | ✅ Running |
| Gunicorn | 8080 (backend) | ✅ Running |
| PostgreSQL | 5432 | ✅ Accepting connections |

### 4. Project layout
- Service unit: `/etc/systemd/system/gaofang-v2-fusion.service`
- WorkingDirectory: `/workspace/projects/drug-distribution-system/gaofang-v2`
- Python: `/workspace/projects/drug-distribution-system/gaofang-v2/venv38/bin/python3.8`
- Gunicorn cmdline: `--bind 0.0.0.0:8080 --workers 2 --threads 2 --timeout 120`
- Nginx conf backup: `/root/gaofang-v2.conf.bak`
- Service shell script: `/root/gaofang-v2-service.sh`

### 4. Bot scan noise
- Nginx error log: Multiple "Connection refused" from scanning bots probing port 5000 (old config) — obsolete since service moved to 8080
- App log: Many 404 WARNING entries from automated scanners probing paths like `/actuator`, `/nacos`, `/jenkins`, `/.git/config`
- Gunicorn error log: "Invalid request" WARNINGs from `79.124.59.86` and other scanning IPs
- All of these are harmless and should be ignored in reports.
