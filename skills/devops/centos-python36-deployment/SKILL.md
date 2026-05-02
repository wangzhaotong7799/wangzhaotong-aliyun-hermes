---
name: centos-python36-deployment
description: CentOS/AlmaLinux 8 Python 3.6 环境部署指南，解决包兼容性问题
tags:
  - centos
  - almalinux
  - python3.6
  - flask
  - deployment
  - bcrypt
related_skills: []
---

# CentOS/AlmaLinux 8 Python 3.6 环境部署指南

适用于 AlmaLinux/CentOS 8 (Python 3.6.8) 环境下的 Python 应用部署，特别是遇到包兼容性问题时的解决方案。

## 当此技能匹配时

关于 Flask 应用的完整部署（含 CentOS/AlmaLinux + Python 3.6 的环境准备、包兼容性、防火墙配置、Gunicorn 迁移、JWT 字节问题、Nginx 反向代理以及部署检查清单），详见下方 **Flask 部署与 Python 3.6 兼容性** 一节。

## Flask 部署与 Python 3.6 兼容性

### Flask 环境配置

在 CentOS/AlmaLinux 8 上部署 Flask（Python 3.6.8），按以下步骤：

#### 依赖包兼容性矩阵

Python 3.6 于 2021 年底 EOL，以下包需要锁定兼容版本：

| 包名 | Python 3.6 版本 | Python 3.8+ 版本 |
|------|----------------|------------------|
| bcrypt | 3.2.2 | 4.x+ |
| Flask | 2.0.3 | 2.3.x+ |
| SQLAlchemy | 1.4.46 | 2.0+ |
| psycopg2-binary | 2.9.3 | latest |
| PyJWT | 2.4.0 | 2.x |
| Werkzeug | 2.0.3 | latest |
| openpyxl | 3.0.10+ | latest |

**典型问题:** `bcrypt` 4.x 要求 Python 3.8+, 在 Python 3.6 上安装失败：
```bash
pip3 install 'bcrypt==3.2.2'
```

#### Flask 启动与公网访问

```python
if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=8080, threaded=True)
```

#### 后台运行

```bash
cd ~/projects/your-app
nohup python3 app.py > service.log 2>&1 &
```

或使用 systemd:
```ini
[Unit]
Description=Flask App
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/path/to/app
ExecStart=/usr/bin/python3 /path/to/app/app.py
Restart=always

[Install]
WantedBy=multi-user.target
```

#### 防火墙配置

```bash
firewall-cmd --permanent --add-port=8080/tcp
firewall-cmd --reload
```

### JWT Token Bytes 格式问题

**症状:** 登录返回 `"token": "b'eyJ0eX...AB_U'"`（bytes 的字符串表示），导致 401

**解决方案:**
```python
def generate_token(user_id, username, roles):
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    if isinstance(token, bytes):
        token = token.decode('utf-8')
    return str(token)
```

### JSON 序列化常见错误

| 场景 | 错误写法 | 正确写法 |
|------|---------|---------|
| SQLite Row 对象 | `user['username']` | `str(user[0] ...)` |
| bcrypt hashpw | `bcrypt.hashpw(...)` | `bcrypt.hashpw(...).decode('utf-8')` |
| 角色列表 | `roles` | `[str(r) for r in roles]` |

### Nginx 反向代理 — 端口一致性

**症状:** 公网访问主页正常，API 请求报 `ERR_CONNECTION_REFUSED`

**根本原因:** Nginx `proxy_pass` 端口与 Flask 实际监听端口不一致

**排查:**
```bash
ss -tlnp | grep python       # 实际端口
grep -r "proxy_pass" /etc/nginx/  # Nginx 配置的端口
```

**修复:** 统一端口，或修改 Nginx 配置：
```bash
sudo sed -i 's/server 127.0.0.1:5000;/server 127.0.0.1:8080;/' /etc/nginx/conf.d/your-site.conf
/www/server/nginx/sbin/nginx -t && /www/server/nginx/sbin/nginx -s reload
```

### 部署检查清单

```bash
#!/bin/bash
echo "1️⃣ 服务进程:" && ps aux | grep "[p]ython3.*app.py"
echo "2️⃣ 端口监听:" && ss -tlnp | grep 8080
echo "3️⃣ 防火墙:" && firewall-cmd --list-ports | grep -q 8080 && echo "✅ 8080 已开放"
echo "4️⃣ 端口一致性:" && N=$(grep "proxy_pass" /etc/nginx/conf.d/*.conf 2>/dev/null | grep -oP ':\K\d+' | head -1) && A=$(ss -tlnp | grep python | grep -oP ':\K\d+' | head -1) && [ "$N" = "$A" ] && echo "✅ 端口一致" || echo "❌ 端口不一致"
echo "5️⃣ 本地 API:" && curl -s http://localhost:8080/api/prescriptions | head -c 100
```

### 参考

详见 Flask Blueprint 和 API 调试技能文档。经验证包含上述全部要点的综合排查流程见 [`flask-api-troubleshooting`](https://hermes-agent.nousresearch.com/docs/skills/flask-api-troubleshooting)。

### bcrypt 兼容性问题

**问题**: `bcrypt` 4.x 要求 Python 3.8+, 在 Python 3.6 环境中安装失败

**错误信息**:
```
Link requires a different Python (3.6.8 not in: '>=3.8')
This package requires Rust >=1.56.0.
```

**解决方案**:

1. **安装兼容版本**:
   ```bash
   pip3 install 'bcrypt==3.2.2'
   ```
   `bcrypt==3.2.2` 是最后一个支持 Python 3.6 的版本

2. **如果需要编译依赖**:
   ```bash
   # 安装 Rust 编译器
   dnf install -y rust
   
   # 或者通过 yum
   yum install -y lang-tools gcc
   ```

### 启动 Flask 应用服务

**配置公网访问**:
```python
if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=8080, threaded=True)
```

**后台运行方式**:

方法 1 - 使用 nohup:
```bash
cd ~/projects/your-app
nohup python3 app.py > service.log 2>&1 &
echo "Service started with PID: $!"
```

方法 2 - 使用 systemd (推荐生产环境):
```bash
# 创建服务文件 /etc/systemd/system/myapp.service
[Unit]
Description=GaoFang Management System
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/projects/MySQL-gaofang
ExecStart=/usr/bin/python3 /root/projects/MySQL-gaofang/app.py
Restart=always

[Install]
WantedBy=multi-user.target

# 启用服务
systemctl daemon-reload
systemctl enable myapp
systemctl start myapp
systemctl status myapp
```

### 验证服务状态

```bash
# 检查端口监听
netstat -tlnp | grep 8080
# 或
ss -tlnp | grep 8080

# 测试本地访问
curl http://localhost:8080/health

# 查看日志
tail -f service.log
```

### 防火墙配置

```bash
# 开放端口 (CentOS/AlmaLinux)
firewall-cmd --permanent --add-port=8080/tcp
firewall-cmd --reload

# 或使用 ufw (Ubuntu/Debian)
ufw allow 8080/tcp
ufw reload
```

## 常见问题：数据库初始化不完整

### 问题现象
启动 Flask 应用后访问 API 返回 500 错误：
```
ERROR - 获取处方记录时出错：no such table: prescription_records
```

**原因**: `init_db.py` 可能只创建了部分辅助表（如 status_change_logs），但未创建主业务表。

### 排查步骤

1. **检查现有表**:
   ```bash
   sqlite3 gaofang.db ".tables"
   # 输出可能只有：status_change_logs, users, roles 等
   # 缺少主业务表：prescription_records
   ```

2. **查找表定义脚本**:
   ```bash
   # 在 app.py 中搜索表创建逻辑
   grep -A 30 "CREATE TABLE.*prescription" app.py
   
   # 或查找数据迁移脚本
   ls -la data_migration.py init_db.py restore_db.py
   ```

3. **从迁移脚本提取表结构**:
   - 打开 `data_migration.py`
   - 找到 `setup_database()` 函数
   - 复制 `CREATE TABLE` SQL 语句

4. **手动创建缺失表**:
   ```bash
   cd ~/projects/your-app
   
   sqlite3 yourapp.db << 'EOF'
   CREATE TABLE IF NOT EXISTS your_table (
       id INTEGER PRIMARY KEY AUTOINCREMENT,
       ...
   );
   
   CREATE INDEX IF NOT EXISTS idx_column ON your_table(column);
   
   .tables  -- 验证表已创建
   EOF
   ```

5. **验证修复**:
   ```bash
   # 重启服务
   pkill -f "python3.*app.py"
   nohup python3 app.py > service.log 2>&1 &
   
   # 测试 API
   curl http://localhost:8080/api/data
   ```

### 预防措施

- 在部署前完整阅读项目文档和数据初始化流程
- 区分"认证系统初始化"(users/roles) 和"业务数据初始化"(主数据表)
- 保留原始数据迁移脚本用于生产环境数据导入

## 关键知识点

1. **Python 版本兼容性检查**:
   - 查看包的最小 Python 版本要求：`pip show package-name`
   - 查询特定版本的 PyPI 页面
   - Python 3.6 已于 2021 年底 EOL，很多新包不再支持

2. **常见不兼容包及替代方案**:
   - `bcrypt>=4.0`: 降级到 `bcrypt==3.2.2`
   - `cryptography`: 可能需要手动编译，确保安装了 Rust
   - 其他包遇到类似问题时，查找最后一个支持 Python 3.6 的版本

3. **数据库初始化陷阱**:
   - `init_db.py` 可能不包含所有表的创建逻辑
   - 有些项目分离了"认证表初始化"和"业务表初始化"
   - 需要通过 `.tables` 命令完整检查数据库状态
### 环境升级建议

- 优先升级到 Python 3.8+（参见下方升级指南）
- 考虑使用 pyenv 管理多个 Python 版本
- 生产环境推荐使用 Docker 容器化部署

### 从 Python 3.6 升级到 Python 3.8+

#### 升级动机
- bcrypt 4.x+ 要求 Python 3.8（3.6 只能锁死 bcrypt==3.2.2）
- 越来越多第三方库放弃 Python 3.6 支持（2021 年底 EOL）
- 升级后可平滑使用 Flask 2.3.x、SQLAlchemy 2.x、现代 psycopg2

#### 前置检查

```bash
# 1. 确认当前版本
python3.6 --version

# 2. 检查系统上 Python 3.8 是否可安装
python3.8 --version || echo "需安装"

# 3. 检查代码是否兼容（Python 3.11 语法检查更严格，通过即 3.8+ 无问题）
find . -name "*.py" -exec python3 -m py_compile {} \; 2>&1

# 4. 检查系统类型（确认可用 EL8 仓库）
cat /etc/redhat-release
# Alibaba Cloud Linux 3 / OpenAnolis / CentOS 8 / AlmaLinux 8 均适用
```

#### 安装 Python 3.8

```bash
# EL8 系统（含 Alibaba Cloud Linux 3 / OpenAnolis）
yum install -y python38 python38-devel

# 验证
python3.8 --version   # → Python 3.8.17
python3.8 -m pip install --upgrade pip setuptools wheel
```

#### 创建虚拟环境并安装依赖

```bash
cd ~/projects/your-app

# 创建 venv
python3.8 -m venv venv38

# 安装依赖（requirements.txt 无需修改即可兼容 3.8）
source venv38/bin/activate
pip install -r requirements.txt

# 特别关注：Flask 版本跳跃
# requirements.txt: Flask>=2.0.0,<3.0.0
# Python 3.6 → pip 安装 Flask 2.0.3
# Python 3.8 → pip 安装 Flask 2.3.3（最新兼容版本）
# 2.0→2.3 无破坏性变更影响常见业务逻辑，如担心可锁定：
# Flask==2.0.3  # 保持原版本
```

#### 验证升级成功

```bash
# 1. 语法检查（全通过 → 无 3.6→3.8 兼容问题）
find . -name "*.py" -exec python3.8 -m py_compile {} \; 2>&1 | grep -v "Errors:" | head -5

# 2. 导入测试（Flask app 创建成功）
cd gaofang-v2 && source venv38/bin/activate
python3.8 -c "
import sys; sys.path.insert(0, '.')
from app import app
for rule in sorted(app.url_map.iter_rules(), key=lambda r: r.rule):
    print(rule.rule, '->', rule.endpoint)
print(f'Total: {len(list(app.url_map.iter_rules()))} routes')
"

# 3. API 实机测试
python3.8 app.py &
sleep 2
curl -s -o /dev/null -w "HTTP %{http_code}\n" http://localhost:8080/
# 登录 → 获取 token → 调用业务 API

# 4. 数据层验证
python3.8 -c "
from app import app, db
with app.app_context():
    result = db.session.execute('SELECT count(*) FROM prescription_records')
    print(f'处方记录数: {result.scalar()}')
"
```

#### 已知升级陷阱

| 问题 | 说明 | 对策 |
|------|------|------|
| Flask 版本跳跃 | requirements.txt `>=2.0.0` 会拉取 2.3.3 | 锁 `Flask==2.0.3` 或测试后升级 |
| 虚拟环境迁移 | 旧 venv 的 Python 3.6 解释器不能直接指向 3.8 | 必须重新创建 venv（`python3.8 -m venv venv38`） |
| 系统 Python 路径混淆 | `python3` 可能仍指向 3.6 | 始终用 `python3.8` 全路径或激活 venv 后运行 |
| 宝塔面板环境 | 面板使用独立 pyenv (3.7+)，不影响系统 Python | 直接安装 python38 无冲突 |
| psycopg2 | Python 3.6 下可能用旧版 | 3.8 下 `psycopg2-binary>=2.9.10` 正常可用 |

#### 系统兼容性备忘

**Alibaba Cloud Linux 3 (OpenAnolis)** — 与 EL8 完全兼容：
- 包管理器：`yum`（非 dnf）
- 仓库名：`alinux3-module` / `alinux3-updates` / `epel`
- Python 3.8 包名：`python38`（在 alinux3-module）
- 已验证 Python 3.8.17 + Flask 2.3.3 + PostgreSQL 13 + psycopg2 2.9.10

#### 升级后注意事项

1. **服务启动命令** — 从 `python3.6 app.py` 改为 `python3.8 app.py` 或 `venv38/bin/python app.py`
2. **systemd 服务文件** — 同步修改 `ExecStart` 中的 Python 路径（参考下方生产切换流程）
3. **监控告警** — 升级后前 24 小时关注日志级别 ERROR 和内存使用
4. **回滚方案** — 保留旧的 `venv/` 或系统全局包，确认可以 `python3.6 app.py` 秒回
5. **Git 提交** — 升级完成后提交 venv 创建方式到项目文档，方便他人复现

#### 生产切换流程（无缝切换运行中服务）

从 Python 3.6 切换到 3.8 时，服务仍在对外提供请求的场景：

```bash
# 步骤 1: 先在新版本上测试（旧版本不受影响）
python3.8 -m venv venv38
source venv38/bin/activate
pip install -r requirements.txt
python3.8 app.py --port 8081 &  # 临时端口测试
curl -s -o /dev/null -w "%{http_code}" http://localhost:8081/
# 确认新版本正常 → 杀掉测试进程

# 步骤 2: 停旧起新
kill $(pgrep -f "python3.6 app.py")   # 杀掉旧服务
source venv38/bin/activate
nohup python3.8 app.py > app.log 2>&1 &
echo "New PID: $!"

# 步骤 3: 验证
sleep 2
curl -s -o /dev/null -w "HTTP %{http_code}\n" http://localhost:8080/

# 步骤 4: 验证核心 API
TOKEN=$(curl -s -X POST http://localhost:8080/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"admin123"}' | \
  python3 -c "import sys,json;print(json.load(sys.stdin)['token'])")
curl -s -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8080/api/prescriptions?limit=1" | head -c 200

# 步骤 5: 更新 .gitignore 防止 venv 被推送
echo -e "\n# 虚拟环境\nvenv/\nvenv*/\n.venv/" >> .gitignore
git add .gitignore && git commit -m "⬆️ .gitignore: exclude venv directories"
```

#### .gitignore 与 venv 管理（易忽略）

**常见错误**: 创建虚拟环境后直接推送，导致：
- 几十 MB 的 site-packages 被推送到 repo
- 不同架构/系统的包冲突
- `.gitignore` 中没有排除模式

**正确的 .gitignore 配置**:
```gitignore
# 虚拟环境 — 必须放在 Python 缓存之前
venv/
venv*/
.venv/
```

**为什么用 `venv*/` 而非 `venv/`**: 如果项目有多个测试环境（`venv38/`、`venv39/`、`venv310/`），`venv*/` 匹配所有前缀为 venv 的目录，`venv/` 只匹配精确的 `venv/`。

## 参考命令清单

```bash
# 检查 Python 版本
python3 --version

# 列出已安装包
pip3 list

# 安装包并指定版本
pip3 install 'package-name==version'

# 查看进程
ps aux | grep python3

# 网络诊断
curl -v http://IP:PORT/path
nc -zv IP PORT

# 数据库快速检查
sqlite3 yourapp.db ".tables"
sqlite3 yourapp.db "SELECT COUNT(*) FROM your_table;"
```
