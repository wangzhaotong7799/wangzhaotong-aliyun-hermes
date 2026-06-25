---
name: "bt-panel-add-existing-python-site"
description: "[ARCHIVED] 已合并到 bt-panel-management — 将已有 Flask/Python Web 应用添加到宝塔面板进行统一管理和反向代理"
tags:
  - archived
  - deployment
  - web-server
  - flask
author: ""
date_created: 2026-04-24
---

# 宝塔面板添加已有 Python Web 应用完整指南

## 概述

当你的 Python/Flask 应用已经在服务器上运行（如通过 Gunicorn），但希望使用宝塔面板统一管理时，本指南提供完整的集成步骤。

## 关键前提：双 Nginx 环境

很多服务器存在**两个独立的 Nginx**：

| Nginx 类型 | 路径 | 用途 |
|-----------|------|------|
| **系统 Nginx** | `/etc/nginx/` | yum/apt安装，systemctl 管理 |
| **宝塔 Nginx** | `/www/server/nginx/` | 宝塔面板自带，独立运行 |

**重要认知:**
- `systemctl nginx` 控制的是系统 Nginx，不是宝塔 Nginx
- `/etc/nginx/conf.d/*.conf` 对宝塔无效
- 宝塔的 vhost 配置在 `/www/server/panel/vhost/nginx/`

## 操作步骤

### 步骤 1: 准备网站目录结构

```bash
mkdir -p /www/wwwroot/<site-name>
chmod 755 /www/wwwroot/<site-name>
mkdir -p /www/wwwlogs
touch /www/wwwlogs/<site-name>_access.log
touch /www/wwwlogs/<site-name>_error.log
```

### 步骤 2: 添加宝塔数据库记录

执行 Python 脚本插入站点和域名记录到 `/www/server/panel/data/db/site.db`:

```python
import sqlite3
from datetime import datetime

conn = sqlite3.connect('/www/server/panel/data/db/site.db')
cursor = conn.cursor()
now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

# sites 表字段：name, path, status, index, ps, addtime, type_id, project_type, rname
cursor.execute('''
    INSERT INTO sites (name, path, status, "index", ps, addtime, type_id, project_type, rname)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
''', ('<site>', '/path/to/project', 'run', '/', '备注', now, 1, 'python', 'domain.com'))

site_id = cursor.lastrowid

# domain 表绑定
cursor.execute('INSERT INTO domain (pid, name, port, addtime) VALUES (?, ?, ?, ?)',
               (site_id, 'domain.com', 80, now))

conn.commit()
conn.close()
```

**注意：** `"index"` 列名需要用双引号包裹，因为它是 SQL 保留字。

### 步骤 3: 创建 Nginx 反向代理配置

**文件位置：** `/www/server/panel/vhost/nginx/<site-name>.conf`

配置要点：
- `listen 80; server_name <domain-or-ip>;`
- `location /api { proxy_pass http://127.0.0.1:<port>/; ... }`
- `location /health { proxy_pass http://127.0.0.1:<port>/health; }`
- `proxy_connect_timeout 60s; proxy_read_timeout 60s;`
- 设置 access_log 和 error_log 路径

参考现有技能 `flask-centos-py36-deployment` 中的反向代理模板。

### 步骤 4: 验证和重载

```bash
/www/server/nginx/sbin/nginx -t        # 测试语法
/www/server/nginx/sbin/nginx -s reload  # 重载配置
curl http://<domain-or-ip>/health       # 验证响应
```

## 常见问题排查

### 问题 1: 访问显示宝塔默认页面或权限错误 (403)

**原因：** 配置文件未加载或被其他默认站点覆盖

```bash
ls -la /www/server/panel/vhost/nginx/
chmod 644 /www/server/panel/vhost/nginx/<site-name>.conf
grep "include.*vhost" /www/server/nginx/conf/nginx.conf
```

**特别注意：** 如果多个 location 块指向不同 root 目录，可能导致冲突：
- 检查 `root` 配置是否指向正确的静态文件目录
- 确保静态文件目录权限正确：`chmod 755 <static-dir>`

### 问题 2: 404 Not Found 或"接口不存在"

**原因可能包括：**
1. `location /api/` 与 `location /api` 匹配规则不同（有斜杠 vs 无斜杠）
2. `proxy_pass` 结尾是否带 `/` 会影响路径处理
   - `proxy_pass http://127.0.0.1:<port>/;` → 保留完整路径
   - `proxy_pass http://127.0.0.1:<port>;` → 会截断匹配部分

**推荐配置：**
```nginx
location /api {
    proxy_pass http://127.0.0.1:<port>/;
}
```

3. 静态文件目录配置错误导致优先匹配
   - 将静态文件 location 放在 API 之前并使用更具体的正则匹配

### 问题 3: 后端连接超时

```bash
netstat -tlnp | grep <port>                    # 确认监听
curl http://127.0.0.1:<port>/health            # 本地测试
tail -f /www/wwwlogs/<site-name>_error.log     # 查看日志
```

### 问题 4: API 不稳定，有时正常有时返回 404

**排查步骤：**
1. **验证 Gunicorn 直连是否正常**
   ```bash
   curl -s http://127.0.0.1:<port>/api/test-endpoint | head -c 200
   ```

2. **验证 Nginx 代理是否正常**
   ```bash
   curl -s http://<your-domain>/api/test-endpoint | head -c 200
   ```

3. **如果 Gunicorn 正常但 Nginx 失败，可能是：**
   - 多个 server 块配置冲突
   - location 优先级问题
   - 其他默认 site 覆盖

4. **重载 Nginx 配置**
   ```bash
   ps aux | grep nginx | grep master
   kill -HUP <nginx-master-pid>
   ```

### 问题 5: 前端页面能加载但功能异常

**常见原因：**
- 前端请求 URL 与 Nginx 代理路径不匹配
- JavaScript 中的 API_BASE_URL 配置错误
- CORS 配置问题（需要`CORS(app, resources={r"/api/*": {"origins": "*"}})`）

## 验证清单

| 检查项 | 命令 | 预期结果 |
|--------|------|----------|
| 数据库记录 | sqlite3 /www/server/panel/data/db/site.db "SELECT * FROM sites" | 包含新站点 |
| 配置文件 | ls /www/server/panel/vhost/nginx/ | 存在 .conf 文件 |
| 配置语法 | /www/server/nginx/sbin/nginx -t | syntax is ok |
| 服务响应 | curl http://domain/health | 返回 JSON/HTML |

## 管理命令

```bash
# 重启宝塔 Nginx
/www/server/nginx/sbin/nginx -s stop && sleep 1 && /www/server/nginx/sbin/nginx

# 重新加载配置（推荐）
/www/server/nginx/sbin/nginx -s reload

# 实时日志
tail -f /www/wwwlogs/<site-name>_access.log
```

## 关键路径总结

- **数据库**: `/www/server/panel/data/db/site.db`
- **主配置**: `/www/server/nginx/conf/nginx.conf`
- **站点配置**: `/www/server/panel/vhost/nginx/`
- **网站根目录**: `/www/wwwroot/<site-name>/`
- **日志目录**: `/www/wwwlogs/`