# Nginx 临时目录权限不足导致文件上传 500

## 症状

Nginx 日志中 POST 请求返回 500，Gunicorn/应用日志无错误。

**Nginx access log：**
```
1.62.185.204 - POST /api/import HTTP/1.1 → 500 (579 bytes)
```

**Nginx error log（关键线索）：**
```
2026/06/02 16:29:56 [crit] 33867#0: *1308 open() "/var/lib/nginx/tmp/client_body/0000000001" failed (13: Permission denied)
```

## 诊断流程

### 第1步：确认错误在 Nginx 层，不在应用层

```bash
# Check nginx error log
grep 'Permission denied' /www/wwwlogs/*_error.log /var/log/nginx/error.log

# Confirm app has no traceback
# gunicorn-error.log shows nothing at the timestamp of the 500
# app.log shows nothing
```

### 第2步：验证权限

```bash
ls -la /var/lib/nginx/
# drwxrwx---  3 nginx root  →  MISSING o+x
ls -la /var/lib/nginx/tmp/
# drwxrwx---  7 nginx root  →  MISSING o+x (www can't traverse)
ls -la /var/lib/nginx/tmp/client_body/
# drwx------  2 www   root  →  www owns it, but can't reach it
```

### 第3步：确认是上传类请求独有问题

测试 GET 请求（正常），POST 无文件（正常），POST 带文件（500）：
```bash
# GET — should work
curl -s -o /dev/null -w "%{http_code}" http://localhost/

# POST without file — depends on handler
curl -s -o /dev/null -w "%{http_code}" -X POST http://localhost/api/import

# POST with file — will 500
curl -s -o /dev/null -w "%{http_code}" -X POST http://localhost/api/import \
  -F "file=@test.xlsx"
```

## 根因

Nginx worker 进程以 `www` 用户运行。上传请求体（`client_body`) 需要写入临时目录 `/var/lib/nginx/tmp/client_body/`。

**路径遍历权限链：**
```
/var/lib/nginx/        770 (owner=nginx,group=root) → www 没权限进出
  └── tmp/             770 (owner=nginx,group=root) → www 没权限进出
      └── client_body/ 700 (owner=www,group=root)   → www 能读写，但到不了这里
```

`www` 用户对 `/var/lib/nginx/tmp/` 的权限是 `---`（其他），无法进入。Nginx 无法创建临时文件来存储上传的请求体 → 500。

## 修复

```bash
# 关键：给上级目录加 o+x（可遍历），www 才能进入
chmod 771 /var/lib/nginx
chmod 771 /var/lib/nginx/tmp
```

其他子目录（`client_body/`, `proxy/`, `fastcgi/`, `scgi/`, `uwsgi/`）保持 700 不变——它们属主已经是 `www`。

## 验证

```bash
# 用带文件的 POST 请求测试
curl -s -X POST "http://localhost/api/import" \
  -F "file=@test.xlsx" \
  -w "\nHTTP %{http_code}"
# → {"message":"导入完成: 新增 1 条"}  200 OK

# Nginx error log 不再有 Permission denied
```

## 复发预防

**复用记录：** 此问题 2026-05-14 首次修复，2026-06-02 复发。根因：系统更新（Nginx 版本升级、安全补丁）可能重建 `/var/lib/nginx/` 目录结构，恢复默认 770 权限。

### 方案 A：cron 定时修复

```bash
# 每 6 小时检查并修复权限
0 */6 * * * chmod 771 /var/lib/nginx /var/lib/nginx/tmp 2>/dev/null
```

通过 Hermes cron：
```yaml
schedule: "0 */6 * * *"
script: |
  chmod 771 /var/lib/nginx /var/lib/nginx/tmp 2>/dev/null
  echo "nginx temp dir permissions refreshed"
no_agent: true
```

### 方案 B：systemd tmpfiles.d 配置

```bash
# 创建持久化权限规则（即使目录被重建也生效）
cat > /etc/tmpfiles.d/nginx-client-body.conf << 'EOF'
# Type Path                    Mode   UID  GID  Age  Argument
d /var/lib/nginx              0771   nginx root  -   -
d /var/lib/nginx/tmp          0771   nginx root  -   -
EOF

systemd-tmpfiles --create /etc/tmpfiles.d/nginx-client-body.conf
```

`tmpfiles.d` 方案更可靠——每个启动时自动应用，不依赖 cron 时间窗口。

## 相关陷阱

- **只有 POST/PUT/PATCH 受影响** — GET 请求不需要写 client_body
- **Gunicorn 错误日志无记录** — Nginx 在转发前就失败了，请求没到 Gunicorn
- **500 响应 body 大小 579 字节** — 这是 Nginx 默认 500 页面，不是应用层错误响应
- **系统更新会覆盖** — `yum update nginx` / `apt upgrade nginx` 可能重新创建目录
