---
name: bt-panel-management
description: 宝塔面板网站全生命周期管理 — 添加现有站点、添加 Python 应用、从面板解绑转为独立运行
tags:
  - devops
  - deployment
  - baota
  - nginx
  - bt-panel

---

# 宝塔面板（BT Panel）网站全生命周期管理

## 总览

本技能涵盖宝塔面板中 Web 应用的完整生命周期管理：将已运行的站点添加至面板管理（通用站点 + Python/Flask 应用），以及将站点从面板解绑转为独立运行。所有操作均涉及**双 Nginx 共存**环境（系统 Nginx vs 宝塔 Nginx）。

### 核心环境认知

| Nginx 类型 | 路径 | 用途 |
|-----------|------|------|
| **系统 Nginx** | `/etc/nginx/` | yum/apt安装，systemctl 管理 |
| **宝塔 Nginx** | `/www/server/nginx/` | 宝塔面板自带，独立运行 |

**重要:** `systemctl nginx` 控制系统 Nginx，不是宝塔的。宝塔的 vhost 配置在 `/www/server/panel/vhost/nginx/`。

---

## 目录

1. [添加现有网站至面板](#一添加现有网站至面板)
2. [添加 Python/Flask 应用至面板](#二添加-pythonflask-应用至面板)
3. [从面板解绑转为独立运行](#三从面板解绑转为独立运行)
4. [常见问题排查](#四常见问题排查)
5. [管理命令速查](#五管理命令速查)

---

## 一、添加现有网站至面板

### 场景

已通过系统 Nginx 部署的 Web 应用，希望纳入宝塔面板统一管理。

### 检查环境

```bash
which nginx
nginx -V 2>&1 | grep prefix
ls /etc/nginx/conf.d/
ls /www/server/nginx/conf/vhost/ 2>/dev/null
netstat -tlnp | grep -E ':80|:443'
```

### 向宝塔数据库添加站点记录

```python
import sqlite3
from datetime import datetime

conn = sqlite3.connect('/www/server/panel/data/db/site.db')
cursor = conn.cursor()
now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

# sites 表字段：name, path, status, "index", ps, addtime, type_id, project_type, rname
cursor.execute('''
    INSERT INTO sites (name, path, status, "index", ps, addtime, type_id, project_type, rname)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
''', ('your-site', '/path/to/project', 'run', '/', '备注', now, 1, 'python', 'domain.com'))
site_id = cursor.lastrowid

# 添加域名绑定
cursor.execute('INSERT INTO domain (pid, name, port, addtime) VALUES (?, ?, ?, ?)',
               (site_id, 'domain.com', 80, now))
conn.commit()
```

**注意:** `"index"` 列名需双引号包裹（SQL 保留字）。

### 创建标准目录结构

```bash
mkdir -p /www/wwwroot/your-site
chmod 755 /www/wwwroot/your-site
mkdir -p /www/wwwlogs
chown -R www:www /www/wwwroot/your-site
```

### 处理 Nginx 配置

**方案 A：使用宝塔 Nginx（推荐）** — 停止系统 Nginx，使用宝塔 Nginx：
```bash
systemctl stop nginx
/www/server/nginx/sbin/nginx
# 在面板中配置反向代理
```

**方案 B：保持系统 Nginx** — 保留现有配置，仅让宝塔做记录。

---

## 二、添加 Python/Flask 应用至面板

### 步骤 1: 准备目录结构

```bash
mkdir -p /www/wwwroot/<site-name>
chmod 755 /www/wwwroot/<site-name>
mkdir -p /www/wwwlogs
touch /www/wwwlogs/<site-name>_access.log
touch /www/wwwlogs/<site-name>_error.log
```

### 步骤 2: 添加数据库记录

同上，注意 `project_type='python'`。

### 步骤 3: 创建 Nginx 反向代理配置

**文件:** `/www/server/panel/vhost/nginx/<site-name>.conf`

```nginx
server {
    listen 80;
    server_name <domain-or-ip>;

    location /api {
        proxy_pass http://127.0.0.1:<port>/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_connect_timeout 60s;
        proxy_read_timeout 60s;
    }

    location /health {
        proxy_pass http://127.0.0.1:<port>/health;
    }

    access_log /www/wwwlogs/<site-name>_access.log;
    error_log /www/wwwlogs/<site-name>_error.log;
}
```

### 步骤 4: 验证

```bash
/www/server/nginx/sbin/nginx -t
/www/server/nginx/sbin/nginx -s reload
curl http://<domain-or-ip>/health
```

---

## 三、从面板解绑转为独立运行

### 适用场景

需要将已在宝塔面板管理的站点转为完全独立运行，不受面板控制。

### 方法 A：保留 vhost 目录引用（简单方案）

配置文件继续放在 `/www/server/panel/vhost/nginx/` 目录，面板操作不会影响。

### 方法 B：完全移至标准位置（推荐）

```bash
# 备份
cp /www/server/panel/vhost/nginx/your-site.conf /root/your-site.conf.bak

# 移动到独立位置
mv /www/server/panel/vhost/nginx/your-site.conf /etc/nginx/conf.d/your-site.conf
```

在主配置中 include：
```bash
sed -i '/^include \/www\/server\/panel\/vhost\/nginx\/\*\.conf;$/a include /etc/nginx/conf.d/your-site.conf;' /www/server/nginx/conf/nginx.conf
```

```bash
/www/server/nginx/sbin/nginx -t && /www/server/nginx/sbin/nginx -s reload
```

### 服务管理脚本

```bash
#!/bin/bash
APP_DIR="/path/to/project"
PID_FILE="/tmp/app.pid"

case "$1" in
    start)
        cd $APP_DIR
        nohup gunicorn --config gunicorn.conf.py --pid $PID_FILE app:app \
            > /www/wwwlogs/app_gunicorn.log 2>&1 &
        ;;
    stop)
        kill $(cat $PID_FILE 2>/dev/null) && rm -f $PID_FILE
        ;;
    status)
        ps aux | grep gunicorn | grep -v grep
        ;;
esac
```

### 方法对比

| 特性 | 方法 A (vhost) | 方法 B (conf.d) |
|------|---------------|----------------|
| 配置位置 | 宝塔专有目录 | 系统标准目录 |
| 被覆盖风险 | 中等 | 低 |
| 推荐度 | 快速方案 | **生产环境推荐** |

---

## 四、常见问题排查

### 问题 1: 访问显示宝塔默认页面或 403
- 检查 `/www/server/panel/vhost/nginx/` 中配置文件权限：`chmod 644`
- 检查 `include` 语句是否正确
- 查看错误日志：`tail -f /www/wwwlogs/<site>_error.log`

### 问题 2: 404 Not Found / 接口不存在
- `location /api/` 与 `location /api` 匹配规则不同
- `proxy_pass` 结尾是否带 `/` 影响路径处理
  - `proxy_pass http://127.0.0.1:port/;` → 保留完整路径
  - `proxy_pass http://127.0.0.1:port;` → 截断匹配部分

### 问题 3: 后端连接超时
```bash
netstat -tlnp | grep <port>
curl http://127.0.0.1:<port>/health
```

### 问题 4: 前端功能异常
- 前端请求 URL 与 Nginx 代理路径不匹配
- JavaScript 中的 API_BASE_URL 配置错误
- CORS 配置问题

### 问题 5: 修改配置后不生效
```bash
# 正确用法（宝塔 Nginx）
/www/server/nginx/sbin/nginx -s reload

# 错误用法（操作系统 Nginx，对宝塔无效）
systemctl reload nginx
```

---

## 五、管理命令速查

| 操作 | 命令 |
|------|------|
| 查看数据库站点 | `sqlite3 /www/server/panel/data/db/site.db "SELECT id, name, rname FROM sites"` |
| 查看域名绑定 | `sqlite3 /www/server/panel/data/db/site.db "SELECT * FROM domain"` |
| 测试 Nginx 语法 | `/www/server/nginx/sbin/nginx -t` |
| 重载配置 | `/www/server/nginx/sbin/nginx -s reload` |
| 查看 nginx.conf | `/www/server/nginx/conf/nginx.conf` |
| 查看错误日志 | `tail -f /www/wwwlogs/<site>_error.log` |
| 重启宝塔 Nginx | `/www/server/nginx/sbin/nginx -s stop && sleep 1 && /www/server/nginx/sbin/nginx` |

### 安全提示

1. 直接修改宝塔数据库前先备份：`cp /www/server/panel/data/db/site.db /www/server/panel/data/db/site.db.backup`
2. SSL 证书可通过宝塔面板一键申请
3. 独立运行的站点需手动管理服务生命周期

## 📋 场景说明

当你已经通过系统 Nginx 直接部署了 Web 应用，希望将其纳入宝塔面板统一管理时，需要解决以下常见问题：

### 典型问题
- 系统自带 Nginx 与宝塔 Nginx 并存冲突
- 手动配置的网站无法在宝塔面板中显示
- 80 端口被默认站点占用

## 🔍 步骤一：检查当前环境状态

```bash
# 检查 Nginx 版本和路径
which nginx
nginx -V 2>&1 | grep prefix

# 查看是否有多套 Nginx
ls /etc/nginx/conf.d/
ls /www/server/nginx/conf/vhost/ 2>/dev/null

# 确认端口占用
netstat -tlnp | grep -E ':80|:443'
```

### 判断依据
| 指标 | 系统 Nginx | 宝塔 Nginx |
|------|-----------|-----------|
| 配置目录 | `/etc/nginx/` | `/www/server/nginx/conf/` |
| 网站目录 | `/usr/share/nginx/html` | `/www/wwwroot/` |
| 日志目录 | `/var/log/nginx/` | `/www/wwwlogs/` |

## 💾 步骤二：向宝塔数据库添加站点记录

### Python 脚本添加网站

```python
import sqlite3
from datetime import datetime

conn = sqlite3.connect('/www/server/panel/data/db/site.db')
cursor = conn.cursor()

now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

try:
    # 添加站点
    cursor.execute('''
        INSERT INTO sites (name, path, status, "index", ps, addtime, type_id, project_type, rname)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        'your-site-name',
        '/path/to/your/project',
        'run',
        '/',
        'Your Application Description',
        now,
        1,                                        # type_id: 1=Nginx, 2=Apache
        'python',
        'your-domain.com'
    ))
    
    site_id = cursor.lastrowid
    
    # 添加域名绑定
    cursor.execute('''
        INSERT INTO domain (pid, name, port, addtime)
        VALUES (?, ?, ?, ?)
    ''', (site_id, 'your-domain.com', 80, now))
    
    conn.commit()
    print(f"✅ 站点已添加，ID: {site_id}")
    
except Exception as e:
    print(f"❌ 错误：{e}")
    conn.rollback()
finally:
    conn.close()
```

## 📁 步骤三：创建标准目录结构

```bash
# 创建网站根目录
mkdir -p /www/wwwroot/your-site-name
chmod 755 /www/wwwroot/your-site-name

# 创建日志目录
mkdir -p /www/wwwlogs
touch /www/wwwlogs/your-site_access.log
touch /www/wwwlogs/your-site_error.log

# 创建简单的 index.html
cat > /www/wwwroot/your-site-name/index.html << 'EOF'
<!DOCTYPE html><html><head><title>Your Site</title></head>
<body><h1>System Running OK</h1></body></html>
EOF
```

## ⚙️ 步骤四：处理 Nginx 配置

### 方案 A：使用宝塔 Nginx（推荐）

如果决定完全迁移到宝塔管理：

```bash
# 停止系统 Nginx
systemctl stop nginx

# 启动宝塔 Nginx
bt start

# 然后在宝塔面板中配置反向代理
```

### 方案 B：保持系统 Nginx（当前环境）

保留现有配置，仅让宝塔做记录：

```nginx
# /etc/nginx/conf.d/your-site.conf
server {
    listen 80;
    server_name your-domain.com;
    
    root /www/wwwroot/your-site-name;
    index index.html;
    
    # API 转发配置需要在宝塔面板或单独配置文件中设置
    location /api/ {
        # 配置反向代理规则
        include proxy_params;
    }
    
    # 日志
    access_log /www/wwwlogs/your-site_access.log;
    error_log /www/wwwlogs/your-site_error.log;
}
```

## 🐛 常见陷阱

### 1. SQL 语法错误

问题：`index` 是 SQL 保留字，需要加引号：

```python
# 正确写法
INSERT INTO sites (name, ..., "index", ...)
```

### 2. 端口冲突

如果访问 IP 返回宝塔默认页面而不是你的站点：

可能的原因：
- nginx.conf 中有 `server_name _;` 的默认块
- 宝塔自身有前端监听可能影响

### 3. 权限问题

确保网站目录权限正确：

```bash
chown -R www:www /www/wwwroot/your-site-name
chmod -R 755 /www/wwwroot/your-site-name
```

## ✅ 验证清单

- [ ] 数据库中有站点记录
- [ ] 网站目录已创建
- [ ] Nginx 配置文件存在且语法正确
- [ ] 后端服务正在运行
- [ ] curl 测试返回预期内容
- [ ] 防火墙端口已开放

## 📝 参考命令总结

```bash
# 查看宝塔数据库中所有网站
sqlite3 /www/server/panel/data/db/site.db "SELECT id, name, rname FROM sites"

# 查看域名绑定
sqlite3 /www/server/panel/data/db/site.db "SELECT * FROM domain"

# 测试 Nginx 配置
nginx -t

# 重载配置
nginx -s reload

# 查看日志实时输出
tail -f /www/wwwlogs/your-site_error.log
```

---

## ⚠️ 注意事项

1. **数据库操作风险**：直接修改宝塔数据库可能导致面板异常，建议先备份：
   ```bash
   cp /www/server/panel/data/db/site.db /www/server/panel/data/db/site.db.backup
   ```

2. **混合环境维护复杂度**：同时运行系统 Nginx 和宝塔 Nginx 会增加维护成本，长期建议使用单一方案

3. **SSL 证书**：手动添加的站点需要单独申请 SSL 证书，可通过宝塔面板一键申请

4. **备份策略**：定期备份整个 `/www/server/panel/data/` 目录