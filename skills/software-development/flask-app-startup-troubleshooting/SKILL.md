---
name: flask-app-startup-troubleshooting
description: Systematic troubleshooting workflow for Flask application startup issues — dependency conflicts, database initialization, JSON serialization errors, firewall problems.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [flask, troubleshooting, deployment, debugging, python36]
    related_skills: [systematic-debugging, centos-python36-deployment, flask-centos-py36-deployment]
---

# Flask 应用启动故障排查指南

## 场景
当 Flask 应用无法正常启动、页面访问失败或 API 返回 500 错误时，按此流程系统性排查。特别适用于 CentOS/AlmaLinux 8 (Python 3.6) 环境。

---

## 标准排查清单

```
□ 1. 检查进程是否存活：ps aux | grep app.py
□ 2. 检查端口监听：netstat -tlnp | grep <port>
□ 3. 检查本地访问：curl localhost:<port>/health
□ 4. 检查日志错误：tail -100 app.log | grep ERROR
□ 5. 检查依赖完整：pip3 list | grep flask
□ 6. 检查数据库表：sqlite3 db ".tables"
□ 7. 检查防火墙：firewall-cmd --list-ports
□ 8. 测试 API 接口：curl -X POST /api/login ...
```

---

## 常见故障及解决方案

### 0. Python 路径冲突（`which python3 ≠ which pip3`）

**典型场景**：Hermes Agent 环境中，`python3` 指向了 Hermes 自身的 venv (3.11)，而 `pip3` 指向系统 Python 3.6。

**症状**：
```
$ python3 -c "import flask"
ModuleNotFoundError: No module named 'flask'

$ pip3 list | grep flask
Flask               2.0.3    ← pip3 说已安装，但 python3 导入失败！
```

**根本原因**：
- `which python3` → `/root/.hermes/hermes-agent/venv/bin/python3` (3.11)
- `pip3 -V` → `python 3.6` (系统 Python)
- 两个命令指向不同的 Python 解释器

**诊断方法**：
```bash
# 确认不一致
which python3    # 可能指向 Hermes venv
pip3 -V          # 可能指向系统 Python 3.6
readlink -f $(which python3)

# 找出有 Flask 的 Python
for p in /usr/bin/python3.6 /usr/libexec/platform-python3.6 /usr/local/bin/python3 /usr/bin/python3; do
  if [ -x "$p" ]; then
    echo "--- $p ---"
    $p -c "import flask; print('Flask', flask.__version__)" 2>&1
  fi
done
```

**解决方案**：使用全路径运行服务。
```bash
# ❌ 错误（可能用错 Python）
cd /path && python3 app.py

# ✅ 正确（明确指定系统 Python 3.6）
cd /path && /usr/bin/python3.6 app.py

# Hermes terminal 中使用
terminal(background=true, command="cd /path && /usr/bin/python3.6 app.py")
```

**预防**：在项目根目录创建 `.python-version` 文件，记录实际使用的 Python 路径。

### 1. 服务进程异常

**症状**：启动命令执行后无响应或立即退出；公网访问返回 502/拒绝连接

**诊断**：
```bash
# 检查应用进程
ps aux | grep -E "python.*app\\.py|gunicorn" | grep -v grep

# 检查端口（注意：App端口 vs Nginx端口 要分别检查！）
ss -tlnp | grep -E '8080|80|5000'

# 检查本地访问
curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/
curl -s -o /dev/null -w "%{http_code}" http://localhost:80/
```

**关键陷阱：Nginx 可能还活着 — 不要只看 Nginx**

⚠️ **场景重现**：用户反馈 "网站打不开"，你检查发现：
- `journalctl -u nginx` 显示几天前的 `bind() failed` 错误日志 → **但这可能是旧日志！**
- 实际 Nginx 进程仍然在运行（`ss -tlnp | grep ':80 '` 显示 nginx 进程存在）
- 真正的问题是 **app 进程无声退出**了（OOM killer 或外部 kill）

**正确思路 — 分开检查两件事**：

```bash
# 1. 先看 PROCESS（不要被端口迷惑）
ps aux | grep app.py           # App 在不在？
ps aux | grep nginx            # Nginx 在不在？

# 2. 再看 PORT
ss -tlnp | grep ':8080 '       # App 端口？
ss -tlnp | grep ':80 '         # Nginx 端口？

# 3. 别信 journalctl — 它显示的是历史，不是当前
# journalctl -u nginx --no-pager -n 20  # ❌ 可能误导
systemctl is-active nginx                 # ✅ 当前状态
```

**常见恢复场景 — 只需重启 App**：
```bash
# Nginx 正常，App 死了
# 不需要动 Nginx！直接重启 App
cd /path/to/app && python3.8 app.py &

# 验证
sleep 2 && curl -s -o /dev/null -w "%{http_code}" http://localhost:80/
# → 200 （Nginx 代理到 App，App 一活就恢复了）
```

**解决**：根据日志定位具体错误（导入失败、配置错误等）

---

### 2. 依赖包版本不兼容

**典型案例：Python 3.6 + bcrypt**

**症状**：
```
ModuleNotFoundError: No module named 'bcrypt'
This package requires Rust >=1.56.0
```

**原因**：
- Python 3.6.8 环境下 bcrypt 4.x 要求 Python 3.8+
- Python 3.6.8 缺少 Rust 编译器导致无法从源码编译

**解决**：
```bash
# 先安装兼容版本（推荐）
pip3 install 'bcrypt==3.2.2'

# 如果需要更高版本，先安装 Rust
dnf install -y rust
pip3 install bcrypt passlib pyjwt
```

**关键点**：
- CentOS/AlmaLinux 8 自带 Python 3.6.8，需特别注意包版本兼容性
- 使用 `--user` 参数或虚拟环境避免系统 Python 污染
- bcrypt 3.2.2 是最后一个支持 Python 3.6 的版本

---

### 3. 数据库表缺失

**症状**：
```
ERROR: no such table: prescription_records
```

**诊断步骤**：
```bash
# 检查数据库文件大小（空文件为 0 字节）
ls -lh *.db

# 列出所有表
sqlite3 gaofang.db ".tables"

# 查看表结构
sqlite3 gaofang.db ".schema <table_name>"
```

**常见原因**：
- 初始化脚本不完整（只创建部分表）
- 数据库文件为空（0 字节）
- init_db.py 只创建了辅助表而非主数据表

**解决**：
```bash
# 方式一：运行完整初始化脚本
python3 init_db.py

# 方式二：手动创建缺失表
sqlite3 gaofang.db <<EOF
CREATE TABLE IF NOT EXISTS prescription_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date DATE NOT NULL,
    prescription_id TEXT NOT NULL UNIQUE,
    patient_name TEXT NOT NULL,
    ...
);
EOF

# 方式三：删除空文件重新初始化
rm -f empty.db && python3 init_script.py
```

---

### 4. JSON 序列化错误

**症状**：
```
TypeError: Object of type 'bytes' is not JSON serializable
```

**原因**：Flask 尝试序列化 bytes 类型对象到 JSON 响应

**排查方法**：
```bash
# 在日志中查找完整 traceback
tail -50 app.log | grep -B 3 -A 10 "Exception on"
```

**典型场景**：
- bcrypt 哈希值未 decode
- JWT token 在某些版本中是 bytes
- sqlite3.Row 返回值类型混用

**解决模式**：

**错误写法**：
```python
return jsonify({
    "token": token,  # 可能是 bytes
    "username": user['username']  # Row 可能不是 dict
})
```

**正确写法**：
```python
return jsonify({
    "token": str(token),  # 显式转换
    "username": str(user[0] if isinstance(user, (list, tuple)) else user['username']),
    "roles": [str(r) for r in roles]
})
```

**关键点**：
- Python 3.6 + Flask 旧版本对二进制数据处理较严格
- 所有可能为 bytes 的字段都要显式转换为 str
- sqlite3.Row 在不同上下文中的行为可能不同

---

### 5. 防火墙端口未开放

**症状**：本地 curl 可访问，公网 IP 无法连接

**诊断和解决**：
```bash
# 检查防火墙状态
systemctl status firewalld
firewall-cmd --list-all

# 开放端口
firewall-cmd --permanent --add-port=8080/tcp
firewall-cmd --reload

# 验证
firewall-cmd --list-ports | grep 8080
```

**快速修复命令**：
```bash
firewall-cmd --permanent --add-port=<port>/tcp && firewall-cmd --reload
```

---

### 6. 权限不足错误

**症状**：API 返回 403 Forbidden

**检查项**：
- 用户角色是否包含所需权限
- API 路由是否正确添加 `@auth_required` 装饰器
- JWT token 是否在请求头中传递

**调试命令**：
```bash
curl -X POST http://localhost:8080/api/test \
  -H "Authorization: Bearer <your_token>" \
  -v
```

---

## 预防措施

1. **启动脚本集成健康检查**：
   ```bash
   sleep 5 && curl -s http://localhost:8080/health || echo "Service failed!"
   ```

2. **日志级别设置合理**：生产环境 INFO，开发 DEBUG

3. **统一错误响应格式**：便于解析和分析

4. **依赖锁定**：使用 requirements.txt 固定版本
   ```txt
   flask==2.3.0
   bcrypt==3.2.2  # Python 3.6 compatible
   ```

5. **数据库初始化脚本完整性检查**：
   ```bash
   sqlite3 gaofang.db ".tables" | wc -l
   # 确保表数量与预期一致
   ```

---

## 附录：Flask 生产部署与服务恢复

### A. Flask Dev Server → Gunicorn + systemd

#### 为什么 app.run() 不适合生产

Flask 开发服务器 `app.run()` 不是设计用于生产环境：
- 单进程单线程（threaded=True 也仍是单进程）
- 无守护机制，进程无声退出后不会自动重启
- 无崩溃日志留存
- 无法通过 systemd 管理生命周期

#### OOM Killer 诊断三板斧

```bash
# 第一斧：确认进程是否真死了
ps aux | grep -E "gunicorn|python.*app"
ss -tlnp | grep -E "PORT|80"

# 第二斧：排除 OOM killer
dmesg -T | grep -iE 'oom|killed|out of memory' | tail -5

# 第三斧：确认启动方式
grep 'app.run(' app.py
systemctl status
ls /etc/systemd/system/*.service
```

#### Systemd 服务文件模板

**方案 A：系统 Python（通用）**
```ini
[Unit]
Description=App - Flask Production
After=network.target postgresql.service

[Service]
Type=simple
User=root
Group=root
WorkingDirectory=/path/to/project

Environment="PATH=/usr/local/bin:/usr/bin:/bin"
ExecStart=/usr/local/bin/gunicorn --bind 0.0.0.0:8080 --workers 2 --threads 2 --timeout 120 --error-logfile /path/to/logs/gunicorn-error.log --access-logfile /path/to/logs/gunicorn-access.log --log-level info app:app

Restart=always
RestartSec=10
OOMScoreAdjust=-800

[Install]
WantedBy=multi-user.target
```

**方案 B：虚拟环境（推荐生产环境）**
```ini
[Unit]
Description=App - Flask Production
After=network.target postgresql.service

[Service]
Type=simple
User=root
Group=root
WorkingDirectory=/path/to/project

# 将 venv/bin 放 PATH 最前面，优先使用 venv 版本的 gunicorn 和其他工具
Environment="PATH=/path/to/project/venv/bin:/usr/local/bin:/usr/bin:/bin"
ExecStart=/path/to/project/venv/bin/gunicorn --bind 0.0.0.0:8080 --workers 2 --threads 2 --timeout 120 --error-logfile /path/to/logs/gunicorn-error.log --access-logfile /path/to/logs/gunicorn-access.log --log-level info app:app

Restart=always
RestartSec=10
OOMScoreAdjust=-800

[Install]
WantedBy=multi-user.target
```

#### 切换运行中 systemd 服务的 Python 版本

**场景**：已经有一个 systemd 服务跑在旧 Python 版本上（如 Python 3.6），需要切换到新虚拟环境（如 Python 3.8 venv）的 gunicorn。

**步骤**：

1. 确认新虚拟环境已创建且 gunicorn 已安装
```bash
/path/to/new/venv/bin/python --version
/path/to/new/venv/bin/pip list | grep gunicorn
```

2. 编写新的 service 文件（注意：`patch` 工具拒绝写入 /etc/systemd/system/，需要用工作区法）
```bash
# 将内容写至临时文件
cat > /tmp/app.service << 'SERVICEOF'
[Unit]
...
ExecStart=/path/to/new/venv/bin/gunicorn ...
...
SERVICEOF

# 复制到系统目录
cp /tmp/app.service /etc/systemd/system/app.service && echo "copied ok"
```

3. 重载 systemd 并重启
```bash
systemctl daemon-reload
systemctl restart app.service
```

4. 验证新 Python 版本生效
```bash
systemctl status app.service --no-pager | head -8
# 确认 Main PID 的行显示的是 /path/to/new/venv/bin/python3.x
```

5. 健康检查
```bash
curl -s -o /dev/null -w "HTTP %{http_code} in %{time_total}s" http://localhost:8080/ && echo ""
```

**⚠️ 坑**：`patch` / `write_file` 等工具无法直接写入 `/etc/systemd/system/`。流程必须是：`write_file` 到 `/tmp/` → `cp` 到 `/etc/systemd/system/` → `systemctl daemon-reload`。

#### Workers 数量参考

| RAM | Workers | Threads |
|-----|---------|---------|
| 1GB | 2 | 2 |
| 2GB | 2-3 | 2 |
| 4GB | 4 | 2 |
| 8GB+ | 4-8 | 4 |

#### 快速诊断脚本

```bash
#!/bin/bash
APP_NAME="$1"
APP_PORT="${2:-8080}"
echo "=== Process ===" && ps aux | grep -E "gunicorn|python.*app" | grep -v grep
echo "=== Port ===" && ss -tlnp | grep -E "$APP_PORT|80"
echo "=== OOM History ===" && dmesg -T | grep -iE 'oom|killed' | tail -5
echo "=== systemd ===" && systemctl list-units --all | grep -i "$APP_NAME"
```

### B. Python 路径冲突恢复

#### 症状

```bash
ModuleNotFoundError: No module named 'flask'
```
但 `pip3 list | grep flask` 显示 Flask 已安装。

#### 根本原因

在 Hermes Agent 环境中，`python3` 可能指向 Hermes 自身 venv (3.11)，而 `pip3` 指向系统 Python 3.6，两者不一致。

```bash
# 诊断
which python3      # → /root/.hermes/hermes-agent/venv/bin/python3 (3.11)
pip3 -V            # → pip 21.3.1 from /usr/local/lib/python3.6/site-packages (python 3.6)
readlink -f $(which python3)
```

#### 解决方案

```bash
# 方案 A：直接使用系统 Python 3.6（推荐）
/usr/bin/python3.6 app.py

# 方案 B：创建 venv
/usr/bin/python3.6 -m venv /path/to/venv
source /path/to/venv/bin/activate
pip install -r requirements.txt

# 方案 C：修改 shebang
#!/usr/bin/python3.6
```

#### 预防措施

1. **始终使用全路径运行服务脚本**
2. **在 Hermes 环境使用 `terminal()` 前，先确认 `which python3` 和 `pip3 -V` 是否一致**
3. **使用 systemd 明确指定 `ExecStart` 的 Python 路径**