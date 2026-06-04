# Cron Job Prompt Authoring Patterns

## Overview

Hermes Agent's cron system runs scheduled tasks as fresh agent sessions with a user-defined prompt. Writing good cron prompts is different from conversational prompts — the agent has no prior context, no memory of what happened yesterday, and must be fully self-contained.

## Golden Rules

1. **No date assumptions** — Cron jobs have no concept of "today", "yesterday", or "last week". Always calculate dates explicitly with `date` commands, or use relative flags like `--today`, `--week`, `--month`.
2. **Self-contained** — Every command, path, and credential must be spelled out. Don't assume the agent knows where TokScale lives or what the health endpoint is.
3. **Fail-open reporting** — If a check fails (service down, API timeout, disk full), the agent must still deliver a report with what worked and what didn't. Never suppress errors.
4. **No Feishu message tool** — Set `deliver: origin` in the cron job definition. The agent just outputs to terminal; the framework handles delivery.
5. **Specific commands, not descriptions** — Embed exact shell commands in the prompt. "Check the service status" is vague; `systemctl is-active nginx` is exact.
6. **Structured output format** — Specify the exact report template (with sections and emoji markers) so output is consistent across runs.

## Pattern: Daily Token Report

```
任务：生成昨日 Token 使用和节约情况报告

请按以下步骤执行并输出报告输出到终端即可（会自动投递到飞书）：

1. 计算昨天的日期（YYYY-MM-DD格式）

2. 用以下命令查询昨日 TokScale 用量明细：
   /root/.hermes/node/bin/tokscale graph --client hermes --since {昨天日期} --until {昨天日期}

3. 用以下命令查询 RTK 压缩节约统计：
   rtk gain

4. 组装报告，格式如下（用中文）：

```
📊 Token 日报 · 2026-05-07

━━━━ 用量统计 ━━━━
• 消息数：XX 条
• Token 总量：XX (输入 XX + 输出 XX + 缓存 XX)
• 费用：$X.XX

━━━━ 压缩节约 ━━━━
• 累计压缩：XX% (已省 XX tokens)
• 昨日命令数：XX 条

━━━━ 综合 ━━━━
• 本月累计：$X.XX
• 缓存命中率：约 96%
```

如果 TokScale 或 RTK 返回错误或无数据，也要如实报告，不要编造。

5. 不要使用飞书消息发送工具，直接输出即可。该输出会自动投递。
```

**Cron schedule**: `0 8 * * *` (daily at 8 AM)
**Skill**: `devops/token-manager`

## Pattern: Website/Server Health Check

```
任务：巡查服务器上运行的网站和服务，输出运行状况报告。

服务器信息：
- IP：39.107.78.58
- 应用：膏方管理系统 V2（Flask + Gunicorn + Nginx）
  - Nginx: port 80
  - Gunicorn/Flask: port 8080
  - 错误日志：/www/wwwlogs/gaofang-v2_error.log

请依次执行以下检查，将结果输出到终端（会自动投递到飞书）：

第一步：检查服务状态
systemctl is-active gaofang-v2-fusion.service
systemctl is-active nginx

第二步：检查 HTTP 端点
curl -s http://127.0.0.1/nginx-health
curl -s -o /dev/null -w "首页: HTTP %{http_code}" http://127.0.0.1/

第三步：检查最近 24 小时的错误日志
tail -50 /www/wwwlogs/gaofang-v2_error.log

第四步：检查数据库连接
python3 -c "import psycopg2; conn = psycopg2.connect(host='localhost', dbname='xxx', user='xxx', password='xxx'); cur = conn.cursor(); cur.execute('SELECT 1'); print('数据库连接: 正常 ✓')"

第五步：磁盘空间检查
df -h / | tail -2

输出报告模板：
🟢 网站运行报告 · 2026-05-07 09:00

━━━━ 服务状态 ━━━━
• gaofang-v2-fusion：✅ 运行中
• Nginx：✅ 运行中

━━━━ HTTP 端点 ━━━━
• Nginx 健康检查：✅ OK
• 首页响应：✅ HTTP 200

━━━━ 错误日志 ━━━━
• 最近24小时新错误：XX 条
• 关键错误：无 / 有（列出）

━━━━ 数据库 ━━━━
• 连接：✅ 正常

━━━━ 系统 ━━━━
• 磁盘使用率：XX%
• 运行天数：XX 天

如果有任何异常（服务停止、HTTP 报错、数据库无法连接、磁盘超过 85%），用 🚨 标记并加粗说明。
```

**Cron schedule**: `0 9 * * *` (daily at 9 AM)

## Key Implementation Details

### Date Calculation in Cron Prompts

Since cron jobs run in fresh sessions with no context, calculate dates explicitly:

```bash
# Yesterday (Linux)
YESTERDAY=$(date -d "yesterday" +%Y-%m-%d)

# Use with TokScale
/root/.hermes/node/bin/tokscale graph --client hermes --since "$YESTERDAY" --until "$YESTERDAY"

# This week start (Monday)
WEEK_START=$(date -d "last monday" +%Y-%m-%d)
```

### Error Log Time Windows

When checking logs for "recent" errors, specify the time window explicitly:

```bash
# Last 24 hours of access log (if log format includes timestamps)
awk -v cutoff="09/May/2026" '$0 ~ /^[0-9]+\/[A-Za-z]+\/[0-9]+/ && $4 > "["cutoff":09:00:00"' /path/to/error.log

# Simple tail is often enough for small-to-medium traffic sites
tail -50 /path/to/error.log
```

### Service Discovery

Before writing a health check cron prompt, discover what to monitor:

```bash
# Running services
systemctl list-units --type=service --state=running

# Web servers
ss -tlnp | grep ':80\|:443\|:8080'

# Nginx configs
grep -r "server_name" /etc/nginx/conf.d/ /etc/nginx/sites-enabled/ 2>/dev/null | grep -v "#"

# Application logs
ls /www/wwwlogs/ 2>/dev/null
```

## Checklist Before Creating a Cron Job

- [ ] Prompt is self-contained (no assumed context, no "as we discussed")
- [ ] Exact commands embedded (not vague descriptions)
- [ ] Date/time calculated explicitly within the prompt
- [ ] Fail-open reporting (agent reports errors, doesn't crash)
- [ ] Output format template specified
- [ ] `deliver: origin` set (or feishu:chat_id for specific delivery)
- [ ] Skill attached if applicable (for tool access like terminal, web)
- [ ] Schedule tested with initial run time in mind

## Script-Based Cron Jobs

### Execution Model

Hermes cron jobs can use a `script:` field instead of a skill/prompt. When a script is set, the scheduler runs it via `subprocess.run([sys.executable, script_path], ...)` — this means **Python only**. Shell scripts (`.sh` with `#!/bin/bash`) will fail with `SyntaxError: invalid syntax` because Python tries to parse bash syntax.

### Conversion Pattern: Bash → Python

When converting a bash script for use as a cron job script:

```python
#!/usr/bin/env python3
"""Gunicorn worker hot-reload — Python version for Hermes cron.

Replaces the original bash script which failed because Hermes cron
executes all scripts with sys.executable (Python), not the system shell.
"""

import subprocess
import sys
from datetime import datetime, timezone, timedelta

# Localize as needed (example: Beijing Time UTC+8)
TZ = timezone(timedelta(hours=8))
def now_local() -> str:
    return datetime.now(TZ).strftime("%Y-%m-%d %H:%M:%S")

def main():
    # Instead of: MASTER_PID=$(systemctl show -p MainPID myservice.service | cut -d= -f2)
    result = subprocess.run(
        ["systemctl", "show", "-p", "MainPID", "my-service.service"],
        capture_output=True, text=True, timeout=10
    )
    if result.returncode != 0:
        print(f"[{now_local()}] ERROR: systemctl failed: {result.stderr.strip()}")
        sys.exit(1)

    output = result.stdout.strip()
    pid_str = output.split("=", 1)[-1].strip() if "=" in output else ""

    if not pid_str or not pid_str.isdigit() or int(pid_str) == 0:
        print(f"[{now_local()}] ERROR: PID not found (output: {output!r})")
        sys.exit(1)

    pid = int(pid_str)

    # Instead of: kill -HUP "$MASTER_PID"
    subprocess.run(["kill", "-HUP", str(pid)], check=True, capture_output=True, timeout=5)

    print(f"[{now_local()}] ✓ HUP sent to PID {pid}")

if __name__ == "__main__":
    main()
```

Key substitutions table:

| Bash idiom | Python equivalent |
|---|---|
| `$(cmd)` / backtick | `subprocess.run(cmd, capture_output=True).stdout.strip()` |
| `pipe \| cut -d= -f2` | Parse `stdout` with `.split()` or regex |
| `kill -HUP "$PID"` | `subprocess.run(["kill", "-HUP", str(pid)], check=True)` |
| `exit 1` | `sys.exit(1)` |
| `date '+%Y-%m-%d'` | `datetime.now().strftime('%Y-%m-%d')` |
| `[ -n "$VAR" ]` | `if var is not None and var.strip():` |

### Pitfalls

- **`sys.executable` is hardcoded** — the scheduler uses `subprocess.run([sys.executable, str(path)])` on line 596 of `cron/scheduler.py`. There is no shebang detection or shell fallback. Do NOT try to work around this by calling `bash /path` from within a Python script — just write pure Python.
- **No environment inheritance** — scripts run with the cron scheduler's environment, which may differ from your interactive shell. Use absolute paths and export any needed env vars in the job prompt.
- **Timeout applies** — default script timeout is 120 seconds (configurable via `HERMES_CRON_SCRIPT_TIMEOUT` env var or `cron.script_timeout_seconds` in config.yaml).
- **Scripts must live in `HERMES_HOME/scripts/`** — the scheduler validates that the resolved script path is within `~/.hermes/scripts/` and rejects anything outside.
