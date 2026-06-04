---
name: web-performance-tuning
description: 网站性能诊断与优化 — 系统化定位慢加载根因并修复，覆盖 Nginx/Gunicorn/Flask 架构
category: devops
---

# 网站性能优化技能

系统化诊断网站加载慢的问题，从网络到后端逐层排查，给出针对性修复方案。

---

## 适用场景

- 用户反馈「网站好慢」「页面加载不出来」「转圈圈」
- 新部署后首次性能评估
- 页面资源加载时间长、白屏时间长
- 已知后端 API 快但页面整体慢

## 诊断流程（自底向上）

### 1. 服务器基础资源检查

```bash
# 内存
free -h

# 磁盘
df -h /

# CPU/内存 TOP 进程
ps aux --sort=-%mem | head -10
```

**关键信号：**
- 内存可用 < 200MB → 内存不足，Swap 活跃
- 磁盘使用率 > 85% → 可能影响读写
- 单个进程内存 > 30% → 需关注

### 2. 服务进程状态

```bash
ss -tlnp | grep -E ':(80|443|5000|8080|8000)'
```

确认 Nginx / Gunicorn / uWSGI 是否在监听。有端口无响应通常是进程卡死（见下方陷阱）。

### 3. 本地响应速度（绕开网络因素）

```bash
# 测试首页和 API
curl -o /dev/null -s -w "HTTP %{http_code} | TTFB: %{time_starttransfer}s | Total: %{time_total}s\n" http://localhost/

# 直接测后端（绕过 Nginx）
curl -o /dev/null -s -w "Backend: HTTP %{http_code} | %{time_total}s\n" http://127.0.0.1:8080/api/prescriptions
```

**判断：** 本地 TTFB < 50ms 说明后端正常，问题出在网络/资源层。TTFB > 200ms 说明后端可能有慢查询或 worker 拥堵。

### 4. CDN 及外部资源检测

```bash
# 测试 CDN 从国内可访问性
timeout 10 curl -s -o /dev/null -w "CDN: %{time_total}s | HTTP %{http_code} | size: %{size_download}\n" "https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css"
```

**关键信号：**
- CDN 耗时 > 1s → **国外 CDN 从国内访问慢**，这是最常见的根因
- 浏览器需要加载多个 CDN 资源（Bootstrap CSS/JS + Chart.js + xlsx），每个慢 1-3s，累积卡死

### 5. Nginx 配置检查

```bash
# 查看当前配置
cat /etc/nginx/conf.d/gaofang-v2.conf

# 检查 gzip 是否开启
grep -i 'gzip' /etc/nginx/nginx.conf /etc/nginx/conf.d/*.conf

# 检查静态文件是否直服
grep -i 'location.*static' /etc/nginx/conf.d/*.conf
```

**常见问题：** gzip 未开启、静态文件走 proxy_pass 而非 alias

### 6. 浏览器端验证（可选）

查看页面 HTML 中 CDN 资源引用：
```bash
grep -oP '(src|href)="(https?://[^"]+)"' templates/*.html static/index.html
```

---

## 三大优化手段

### 1. CDN 自托管（最大的效果来源）

**步骤：**

```bash
# 下载资源到 static/lib/
mkdir -p static/lib/css static/lib/js

# 下载 Bootstrap
curl -s -o static/lib/css/bootstrap.min.css \
  "https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css"
curl -s -o static/lib/js/bootstrap.bundle.min.js \
  "https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"

# 下载 Chart.js
curl -s -o static/lib/js/chart.umd.min.js \
  "https://cdn.jsdelivr.net/npm/chart.js"

# 下载 datalabels 插件
curl -s -o static/lib/js/chartjs-plugin-datalabels.min.js \
  "https://cdn.jsdelivr.net/npm/chartjs-plugin-datalabels"

# 下载 xlsx
curl -s -o static/lib/js/xlsx.full.min.js \
  "https://cdn.jsdelivr.net/npm/xlsx@0.18.5/dist/xlsx.full.min.js"
```

**HTML 中替换 CDN 链接为本地路径：**

```
  <link href="/static/lib/css/bootstrap.min.css" rel="stylesheet">
  <script src="/static/lib/js/bootstrap.bundle.min.js"></script>
  <script src="/static/lib/js/chart.umd.min.js"></script>
  <script src="/static/lib/js/chartjs-plugin-datalabels.min.js"></script>
  <script src="/static/lib/js/xlsx.full.min.js"></script>
```

### 2. Nginx 直服静态文件

在 Nginx server block 中，proxy_pass 之前加入：

```nginx
location /static/ {
    alias /path/to/your/project/static/;
    expires 7d;
    add_header Cache-Control "public, immutable";
    access_log off;
}
```

**原理：** Nginx 直接发送磁盘文件（零 Python 开销），响应时间从 ~10ms 降至 <1ms。

### 3. 开启 Gzip 压缩

```nginx
gzip on;
gzip_min_length 100;
gzip_comp_level 5;
gzip_types text/plain text/css application/json application/javascript text/xml application/xml application/vnd.ms-excel image/svg+xml;
gzip_vary on;
gzip_proxied any;
```

**效果：** JS/CSS/HTML 压缩到原来的 30%~40%，传输量减少 60-70%。

---

## 陷阱与注意事项

### 陷阱 1：IPv4 vs IPv6 导致 Nginx 路由错误

**现象：** Nginx 配置正确，但 `curl http://localhost/` 返回默认页面而非应用页面。  
**排查：** curl 默认连接 `::1`（IPv6），而 server 只监听了 `0.0.0.0:80`（IPv4）。  
**修复：** 添加 IPv6 监听 `listen [::]:80 default_server;`。  
**验证：** 用 `http://127.0.0.1/`（强制 IPv4）和 `http://[::1]/`（强制 IPv6）分别测试。

### 陷阱 2：Gunicorn 进程卡死

**现象：** ss 显示端口在监听，但 curl 请求超时。  
**典型症状链：** 用户反馈「一直转圈」→ 检查发现首页 HTML 加载快（已被 Nginx 直服）→ 但登录/数据请求一直转 → 实际是 Gunicorn worker 卡死，不是网络/性能问题。

#### 错误日志模式

Gunicorn worker 卡死时，Nginx error log 会出现以下特征：

```
upstream timed out (110: Connection timed out) while reading response header from upstream
```

**关键：** 错误是 `while reading response header`（连接已建立，但 worker 挂死不返回），不是 `connect() failed`（进程死亡端口消失）。

#### 诊断方法（选择性卡死）

Gunicorn worker 卡死时，**不同路由卡死表现不同**——有的能响应，有的挂死。这是因为每个 worker 处理不同的请求，部分 worker 冻住而部分还能处理简单请求。需要逐个测试：

```bash
# 1. 测试根路由（最容易卡死，因为涉及文件读取或模板渲染）
timeout 5 curl -s -o /dev/null -w "Root: HTTP %{http_code} | %{time_total}s\n" http://127.0.0.1:8080/

# 2. 测试 API 路由（最简单的 JSON 查询，可能还能响应）
timeout 5 curl -s -o /dev/null -w "API: HTTP %{http_code} | %{time_total}s\n" http://127.0.0.1:8080/api/prescriptions?page=1\&page_size=3

# 3. 测试登录路由（涉及数据库查询，最容易卡死）
timeout 5 curl -s -o /dev/null -w "Login: HTTP %{http_code} | %{time_total}s\n" \
  'http://127.0.0.1:8080/api/auth/login' -X POST \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"admin123"}'
```

**判断标准：**
- `根路由 /` 超时 + `API` 正常 = **worker 选择性卡死**（部分 worker 冻住，部分还活着）
- 所有路由都超时 = **进程死亡/端口消失**（ss 检查端口是否存在）
- 秒级响应 → 后端正常，排查其他层

#### 修复：HUP 热重启（零中断）

```bash
# 找 master PID
systemctl status gaofang-v2-fusion.service | grep 'Main PID'

# 或者从 ss 输出找（master 是进程树中最老的）
ss -tlnp | grep 8080

# 发 HUP 信号——worker 逐个重启，TCP 连接不中断
kill -HUP <MASTER_PID>
```

**HUP 后观察：** 重启期间可能出现短暂 **502 Bad Gateway**（旧 worker 已退出，新 worker 正在启动），一般 2-3 秒恢复。

#### 验证恢复

```bash
# HUP 后等 3 秒
sleep 3

# 逐个测试关键路由
timeout 5 curl -s -o /dev/null -w "Home: HTTP %{http_code} | %{time_total}s\n" http://127.0.0.1/
timeout 5 curl -s -o /dev/null -w "Login: HTTP %{http_code} | %{time_total}s\n" \
  'http://127.0.0.1/api/auth/login' -X POST \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"admin123"}'
timeout 5 curl -s -o /dev/null -w "API: HTTP %{http_code} | %{time_total}s\n" \
  'http://127.0.0.1/api/prescriptions?page=1&page_size=3'
```

#### 预防方案

Gunicorn 卡死通常是内存泄漏或长时间运行后死锁。三层防御：

**第一层：`--max-requests` 定期重置 worker**
```bash
--max-requests 1000 --max-requests-jitter 200
```
每个 worker 处理 800-1200 个请求后自动退出重建，防止内存持续增长。

**第二层：每日 HUP cron 主动轮换**
即使 `--max-requests` 挡不住，每天凌晨自动热重启一次，确保 worker 不超过 24 小时寿命。

**推荐方法：使用 `systemctl kill -s HUP`（最简单可靠）**
```bash
#!/bin/bash
# 每天凌晨 6 点 cron 触发 — 无需找 PID，systemctl 自动处理
systemctl kill -s HUP gaofang-v2-fusion.service
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Gunicorn HUP sent via systemctl"
```

**备选方法：通过 Gunicorn master PID**
```bash
#!/bin/bash
MASTER_PID=$(systemctl show -p MainPID gaofang-v2-fusion.service 2>/dev/null | cut -d= -f2)
if [ -n "$MASTER_PID" ] && [ "$MASTER_PID" -gt 0 ] 2>/dev/null; then
    kill -HUP "$MASTER_PID"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Gunicorn HUP sent to PID $MASTER_PID"
fi
```

**Python 版本（适用于 Hermes Agent cron 的 `script` 字段）**
Hermes Agent cron 支持 `script` 字段，指向 `/root/.hermes/scripts/<name>.py`：
```python
#!/usr/bin/env python3
import subprocess, syslog, sys

SERVICE = "gaofang-v2-fusion.service"

result = subprocess.run(["systemctl", "is-active", SERVICE],
                        capture_output=True, text=True)
if result.stdout.strip() != "active":
    syslog.syslog(syslog.LOG_WARNING, f"Service {SERVICE} not active, skipping")
    sys.exit(1)

result = subprocess.run(["systemctl", "kill", "-s", "HUP", SERVICE],
                        capture_output=True, text=True)
if result.returncode == 0:
    syslog.syslog(syslog.LOG_INFO, f"SIGHUP sent to {SERVICE}, graceful reload")
else:
    syslog.syslog(syslog.LOG_ERR, f"Failed: {result.stderr.strip()}")
    sys.exit(1)
```

cron 配置（shell）：
```cron
0 6 * * * /path/to/gunicorn-daily-reload.sh
```

Hermes cron 配置（job.json 中设置 `"script": "gunicorn-daily-reload.py"` 即可自动执行）。

**第三层：Nginx 直服首页（兜底）**
即使 Gunicorn 彻底卡死，用户至少能看到页面（见下方"进阶：Nginx 直服首页"）。

**进阶：Nginx 直服首页绕过卡死**
如果 Gunicorn 频繁卡死，可以将首页 `/` 交由 Nginx 直接返回（零 Gunicorn 依赖），即使用户登录不了，至少能看到页面：

```nginx
# 在 proxy_pass 的 location / 之前
location = / {
    try_files /index.html =404;
    root /workspace/projects/drug-distribution-system/gaofang-v2/static/;
    access_log /var/log/nginx/access.log;
}
```

**原理：** `location = /`（精确匹配优先级高于 `/`）让 Nginx 直接从磁盘读 index.html 返回，Gunicorn 卡死不影响首页加载。

### 陷阱 2b：Worker 线程池耗尽导致间歇性 504（非卡死）

**现象：** Nginx 日志中出现间歇性 504，同一请求有时成功有时超时。**有别于陷阱 2**: worker 并未卡死（端口在监听、部分请求仍能响应），而是所有 worker 线程都被占满时新请求排队超时。

**典型日志模式：**

```
# Nginx access log 显示相同 endpoint 有时 200 有时 504
1.62.185.204 - GET /api/prescriptions?status=欠药&patient_name=CL&page=4  → 200  (615 bytes)
1.62.185.204 - GET /api/prescriptions?status=欠药&patient_name=CL&page=4  → 504  (569 bytes)
1.62.185.204 - GET /api/prescriptions?status=欠药&patient_name=CL&page=4  → 200  (63 bytes)
```

**Nginx error log：**
```
upstream timed out (110: Connection timed out) while reading response header from upstream
```

**关键区别判断矩阵：**

| 特征 | Worker 卡死（陷阱 2） | 线程池耗尽（陷阱 2b） |
|------|----------------------|----------------------|
| 部分请求能否响应 | ⛔ 全部超时 | ✅ 简单请求能响应 |
| 响应耗时分布 | 全部超时 | 忽快（<10ms）忽慢（超时） |
| Nginx 错误 | 超时读响应头 | 超时读响应头（同） |
| Gunicorn 错误日志 | 无新日志 | 无新日志 |
| 后端 curl 直测 | 偶尔超时 | 始终正常（<5ms） |
| PostgreSQL 慢查询 | 可能有 | 无慢查询 |
| 触发条件 | 运行时间久 | 用户高频操作 |

#### 诊断流程

```bash
# Step 1: 直测 upstream（绕过 Nginx）— 确认后端本身正常
curl -s -o /dev/null -w "HTTP %{http_code} | %{time_total}s\n" http://127.0.0.1:8080/

# Step 2: 测试并发 — 看是否有排队现象
for i in $(seq 1 10); do
  time curl -s -o /dev/null http://127.0.0.1:8080/api/prescriptions?page=1\&page_size=5 &
done
wait

# Step 3: 检查 Nginx access log 中 504 的触发模式
# 看是否集中在某个时间段/某个操作后大量出现
tail -100 /www/wwwlogs/gaofang-v2_access.log | grep -c " 504 "

# Step 4: 检查 PostgreSQL 当前活跃连接
psql -U app_user -d app_db -c "SELECT count(*), state FROM pg_stat_activity GROUP BY state;"

# Step 5: 计算并发容量
# Gunicorn: workers × threads = 2 × 2 = 4 并发
# 高峰期用户请求量可通过 access log 估算
awk '{print $4}' /www/wwwlogs/gaofang-v2_access.log | sort | uniq -c | sort -rn | head -10
```

#### 常见触发场景

**场景 A：分页查询中的 Python 层过滤导致无效翻页**

这是最常见的触发链。

**典型代码 bug（from 膏方 V2 `api/v1/prescriptions.py`）：**
```python
# SQL 层分页（status 过滤，但 patient_name 不在 SQL 中）
query = session.query(PrescriptionRecord).filter(PrescriptionRecord.status == status)
query = query.order_by(PrescriptionRecord.id.desc())
total = query.count()  # ← 统计的是 status 匹配的总数
query = query.offset((page-1) * page_size).limit(page_size)
records = query.all()  # ← 取出的未经过 patient_name 过滤

# Python 层做 patient_name 拼音匹配（过滤在分页之后！）
for record in records:
    if patient_name:
        patient_pinyin = get_pinyin(record.patient_name)
        if match:
            result.append(record)
# ← 分页在过滤之前，用户翻到的页面可能全是空数据！
```

**触发链条：**
1. 用户搜索患者名拼音（如 "CL"），前端翻到第 4 页
2. API 取第 4 页（offset=150）的 50 条 → Python 拼音过滤后 0 条匹配
3. 前端显示空页面 → 用户以为没加载完，反复点击
4. 快速点击产生大量并发请求 → 4 个 worker 线程全部被占满
5. 后续请求排队等待 → Nginx 60s 超时 → **504**
6. 浏览器自动重试 → 雪上加霜

**修复方法（两层）：**

**修复 1：SQL 层加粗筛（立即见效）**
```python
# 在 SQL 层先用 LIKE 粗筛，减少 Python 层处理量
if patient_name:
    # 先用 SQL 粗筛（减少记录数），再在 Python 层做精确的拼音匹配
    query = query.filter(
        PrescriptionRecord.patient_name.ilike(f'%{patient_name}%')
    )
    # 注意：ilike 只能匹配汉字，拼音搜索仍需 Python 层
```

**修复 2：分页基于匹配后的结果集（根治）**

**核心思路：** 先用 `query.with_entities()` 复用已有查询条件，只取 id+patient_name 做轻量拼音匹配，再分页，最后取完整记录。

```python
# 方案 A（推荐）：轻量查询 + Python 匹配 + 精准分页
if patient_name:
    # Step 1: 复用已有查询条件，只取 id+patient_name（轻量查询）
    id_name_pairs = [
        (r.id, r.patient_name)
        for r in query.with_entities(
            ModelClass.id,
            ModelClass.patient_name
        ).all()
    ]

    # Step 2: Python 层拼音匹配
    matched_ids = []
    for rid, rname in id_name_pairs:
        if pinyin_match(rname or '', patient_name):
            matched_ids.append(rid)

    total = len(matched_ids)

    # Step 3: 分页
    if page and page_size:
        page_ids = matched_ids[(page - 1) * page_size : page * page_size]
    else:
        page_ids = matched_ids[:page_size] if page_size else matched_ids

    # Step 4: 取当前页完整记录
    if page_ids:
        records = (
            session.query(ModelClass)
            .filter(ModelClass.id.in_(page_ids))
            .order_by(ModelClass.id.desc())
            .all()
        )
    else:
        records = []

    result = [r.to_dict() for r in records]

# 方案 B（简单场景）：先取全部 id 后过滤
if patient_name:
    all_ids = [r.id for r in query.all() if pinyin_match(r.patient_name, patient_name)]
    total = len(all_ids)
    page_ids = all_ids[(page-1)*page_size : page*page_size]
    records = query.filter(ModelClass.id.in_(page_ids)).all()
else:
    total = query.count()
    records = query.offset(...).limit(...).all()
```

**⚠ 陷阱：不要用 SQLAlchemy 内部 API `query._whereclause`**

```python
# ❌ 错误做法 — _whereclause 是 SQLAlchemy 内部属性，API 不稳定
query._whereclause  # 访问 SQLAlchemy 内部，版本升级可能失效

# ✅ 正确做法 — with_entities() 复用已有 query 的所有条件
query.with_entities(ModelClass.id, ModelClass.patient_name).all()
# with_entities() 会保留 WHERE/ORDER BY 等已有条件，只替换 SELECT 列
```

#### 修改 systemd 和 Nginx 的 sed 命令

修改 systemd service（workers/threads）：

```bash
sed -i 's/--workers 2 --threads 2/--workers 4 --threads 4/' /etc/systemd/system/gaofang-v2-fusion.service
systemctl daemon-reload
systemctl restart gaofang-v2-fusion.service
```

修改 Nginx timeout（对齐 Gunicorn --timeout）：

```bash
sed -i 's/proxy_read_timeout 60s;/proxy_read_timeout 120s;/; s/proxy_send_timeout 60s;/proxy_send_timeout 120s;/' /etc/nginx/conf.d/gaofang-v2.conf
nginx -t && nginx -s reload
```

**注意：** `patch` 工具拒绝写入 `/etc/` 下系统文件，必须用 `terminal` + `sed`。

**场景 B：前端连击效应**

即使没有场景 A 的 bug，以下操作组合也能耗尽线程池：
- 用户快速连续点击搜索、翻页、筛选
- 浏览器同时发起多个请求（页面加载 + 统计 + 图表）
- 移动端弱网环境下的自动重试

**预防方案：** 前端做请求去重/防抖（debounce），为搜索框添加 300ms 防抖。

#### 扩容方案

Gunicorn 并发容量 = `workers × threads`。计算合理值：

```bash
# 当前值（通常太小）：
# workers=2, threads=2 → 4 并发

# 建议值（针对 4GB 以下内存的轻量应用）：
# workers=4, threads=4 → 16 并发
# 或 workers=2, threads=8 → 16 并发（更省内存）
```

**修改 systemd service 配置：**
```bash
# 编辑 /etc/systemd/system/gaofang-v2-fusion.service
# 在 ExecStart 行修改参数：
ExecStart=/path/to/venv/bin/gunicorn \
  --bind 0.0.0.0:8080 \
  --workers 4 \
  --threads 4 \
  --max-requests 1000 \
  --max-requests-jitter 200 \
  --timeout 120 \
  app:app

# 重载并重启
systemctl daemon-reload
systemctl restart gaofang-v2-fusion.service
```

**对齐 Nginx proxy_read_timeout：**
确保 Nginx 的 `proxy_read_timeout >= Gunicorn --timeout`：
```nginx
proxy_connect_timeout 60s;
proxy_send_timeout 60s;
proxy_read_timeout 120s;  # ← 改为 >= Gunicorn timeout
```

### 陷阱 3：静态文件路径 alias 末尾斜杠

Nginx `alias` 结尾需要与 `location` 匹配斜杠规则：
```nginx
location /static/ {       # 有斜杠
    alias /path/static/;  # 有斜杠，匹配
}
```

### 陷阱 4：错误日志中的扫描器噪音

Nginx 错误日志中大量 404 不一定代表网站有问题。外部扫描器会试探大量不存在的路径（`chart.js`、`Chart.js`、`xlsx.js`、`app.css` 等各种大小写/变体）。

**判断方法：** 查看 HTML 模板中是否真的引用了这些文件。如果模板引用的是 `chart.umd.min.js` 而报错的是 `chart.js` — 这是扫描器，不是真实错误。

详细判断流程见 `references/nginx-error-log-scanner-noise.md`。

### 陷阱 5：重载 Nginx 后配置未生效

```bash
nginx -t          # 先验证语法
nginx -s reload   # 再重载
```

如果语法错误，reload 不会生效，旧配置继续运行。

### 陷阱 6：Nginx 临时目录权限不足 → 文件上传类请求 500

**现象：** POST/PUT 请求带文件（Excel 导入、图片上传等）返回 500，但 GET 请求正常。应用层日志无错误，Nginx error log 报 `Permission denied`。

**Nginx error log：**
```
[crit] open() "/var/lib/nginx/tmp/client_body/0000000001" failed (13: Permission denied)
```

**根因：** Nginx worker（以 `www` 用户运行）需要写 `client_body` 临时目录来存储上传的请求体。但各级父目录 `/var/lib/nginx/` 和 `/var/lib/nginx/tmp/` 权限为 770（缺 o+x），`www` 用户无法遍历进入。

**修复：**
```bash
chmod 771 /var/lib/nginx
chmod 771 /var/lib/nginx/tmp
```

**复发预防：** 系统更新可能重建目录结构恢复默认权限。两种方案：
- **cron 每 6 小时修复：** `0 */6 * * * chmod 771 /var/lib/nginx /var/lib/nginx/tmp`
- **systemd tmpfiles.d（推荐）：** 在 `/etc/tmpfiles.d/nginx-client-body.conf` 声明持久权限

完整诊断步骤和预防方案见 `references/nginx-client-body-permissions.md`。

---

## 参考文件索引

| 文件 | 说明 |
|:----|:----|
| `references/nginx-error-log-scanner-noise.md` | 区分真正错误与扫描器噪音 |
| `references/nginx-performance-config.md` | Nginx 性能配置模板 |
| `references/nginx-client-body-permissions.md` | Nginx 临时目录权限修复指南 |
| `references/cdn-self-hosting.md` | CDN 自托管操作步骤 |
| `references/hermes-cron-script-mechanism.md` | Hermes cron 脚本机制说明 |
