---
name: flask-dev-server-to-gunicorn-systemd
description: "[已合并到 flask-app-startup-troubleshooting] 从 Flask dev server 迁移到 Gunicorn + systemd 生产部署"
version: 1.0.0
tags: [archived, flask, gunicorn, systemd, deployment, production, oom, troubleshooting]
---

# Flask Dev Server → Gunicorn + systemd 生产部署升级

## 场景

Flask 应用在生产环境使用 `app.run()`（Flask 开发服务器）运行，但经常出现进程静默消失、服务不可用、无法自动恢复的问题。

## 根因分析三板斧

### 第一斧：确认进程是否真死了

Check ps, ss/tlnp, and app log tail. If logs show recent activity but process is gone, the process was silently killed.

### 第二斧：排除 OOM killer

Use `dmesg -T | grep -iE 'oom|killed|out of memory'` to check if the target process was OOM-killed. If dmesg has no record matching your app name, OOM is not the cause — OOM killer always leaves a log entry.

### 第三斧：确认启动方式

Check `grep 'app.run(' app.py`, `systemctl status`, and whether a systemd unit file exists in `/etc/systemd/system/`.

## 根本原因

Flask 开发服务器 `app.run()` 不是设计用于生产环境：
- 单进程单线程（threaded=True 也仍是单进程）
- 无守护机制，进程无声退出后不会自动重启
- 无崩溃日志留存
- 无法通过 systemd 管理生命周期
- Flask 启动时明确提示 "Do not use it in a production deployment"

## 修复方案：Gunicorn + systemd

### Step 1: Systemd 服务文件

```ini
[Unit]
Description=App Name - Flask Production
After=network.target postgresql.service
Requires=postgresql.service

[Service]
Type=simple
User=root
Group=root
WorkingDirectory=/path/to/project

Environment="PATH=/usr/local/bin:/usr/bin:/bin"
Environment="FLASK_APP=app.py"
ExecStart=/usr/local/bin/gunicorn --bind 0.0.0.0:8080 --workers 2 --threads 2 --timeout 120 --error-logfile /path/to/logs/gunicorn-error.log --access-logfile /path/to/logs/gunicorn-access.log --log-level info app:app

Restart=always
RestartSec=10
OOMScoreAdjust=-800

[Install]
WantedBy=multi-user.target
```

### Step 2: 安装并启动

```
cp the service file to /etc/systemd/system/
systemctl daemon-reload
systemctl enable <app>
systemctl start <app>
systemctl status <app>
```

### Step 3: Workers 数量

1GB RAM → workers=2, threads=2; 2GB → 2-3; 4GB → 4; 8GB+ → 4-8.

### Step 4: Nginx 反代

Configure an upstream block pointing to localhost:8080, listen on port 80, proxy_pass to the upstream. Set proxy timeouts to 60s, client_max_body_size to 100M.

## OOM 保护

### systemd 级别
Set `OOMScoreAdjust=-800` in the service file. Range: -1000 (never kill) to 1000 (always kill first).

### 系统级别
```
sysctl vm.swappiness=10
sysctl vm.overcommit_memory=2
```
Persist these in /etc/sysctl.conf.

### 验证
```
cat /proc/$(systemctl show -p MainPID <service> --value)/oom_score_adj
```

## 验证清单

- systemctl is-enabled → enabled
- systemctl status → active (running)
- Port is listening
- Local curl returns HTTP 200
- Public HTTP access works
- oom_score_adj matches config

## 常见陷阱

### 1. app.run() 和 Gunicorn 共存
Gunicorn 加载 `app = create_app()` 模块级变量，`if __name__ == '__main__'` 块不会执行，两者不冲突。

### 2. Python 版本冲突（Hermes Agent 环境）
Hermes 有自己的 venv，可能和系统 Python 不同。在 ExecStart 中始终使用全路径 `/usr/local/bin/gunicorn`。如果 Gunicorn 报 "Worker failed to boot"，检查 Python 版本和 SQLAlchemy 兼容性（Python 3.6 需要 SQLAlchemy < 1.4）。

### 3. 内存消耗
app.run() 开发服务器 ~40-80MB 单进程；Gunicorn 2 workers ~190-240MB total。

## 快速诊断脚本

```bash
#!/bin/bash
APP_NAME="$1"
APP_PORT="${2:-8080}"

echo "=== 1. Process ==="
ps aux | grep -E "gunicorn|python.*app" | grep -v grep

echo "=== 2. Port ==="
ss -tlnp | grep -E "$APP_PORT|80"

echo "=== 3. OOM History ==="
dmesg -T | grep -iE 'oom|killed' | tail -5

echo "=== 4. systemd ==="
systemctl list-units --all | grep -i "$APP_NAME"

echo "=== 5. Log tails ==="
for f in app.log logs/*.log; do
  [ -f "$f" ] && echo "--- $f ---" && tail -3 "$f"
done
```
