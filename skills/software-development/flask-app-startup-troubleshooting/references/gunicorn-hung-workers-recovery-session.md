# Gunicorn Workers 卡死恢复实战记录

**日期**：2026-05-15
**系统**：嵩方融合版V2（Flask + PostgreSQL + Gunicorn + Nginx）
**症状**：网站能加载 HTML 和静态文件，但 API 请求全部超时

## 现场日志

### Nginx 访问日志（最终用户访问序列）

```
221.212.192.35 - - [15/May/2026:08:13:56] "GET /" → 304          # 页面加载（缓存）
221.212.192.35 - - [15/May/2026:08:13:56] "GET /static/js/page-prescriptions.js" → 304  # JS 加载
221.212.192.35 - - [15/May/2026:08:14:08] "GET /static/js/common.js" → 499  # 客户端超时断开
221.212.192.35 - - [15/May/2026:08:14:08] "GET /static/css/style.css" → 499  # 客户端超时断开
221.212.192.35 - - [15/May/2026:08:15:11] "GET /" → 504 569      # 网关超时
```

**模式分析**：
- HTTP 304 → nginx 返回缓存，未到达 upstream
- HTTP 499 → nginx 已连接到 upstream（gunicorn），但等待响应时客户端超时断开
- HTTP 504 → nginx 尝试连接 upstream 但超时

### Nginx 错误日志

```
2026/05/15 08:15:11 [error] 307389#0: *4335 upstream timed out (110: Connection timed out)
    while reading response header from upstream,
    client: 221.212.192.35, server: _,
    request: "GET / HTTP/1.1",
    upstream: "http://127.0.0.1:8080/",
    host: "39.107.78.58"
```

### 诊断过程

```bash
# 第一步：ss 显示 gunicorn 在监听
ss -tlnp | grep 8080
# → LISTEN 0 2048 0.0.0.0:8080 0.0.0.0:*  users:(("gunicorn",pid=545162,fd=7),...)

# 第二步：curl 测试本地连接
curl -s --connect-timeout 5 --max-time 10 http://127.0.0.1:8080/
# → FAILED: curl HTTP 000 (超时！)
# 这确认了问题在 gunicorn，不在 nginx

# 第三步：检查进程状态
cat /proc/545162/status | head -5
# → Name: gunicorn, State: S (sleeping)
# 进程活着但卡死

# 第四步：进程运行时长
# systemctl 显示自 2026-05-12 起运行，共 3 天
```

### 恢复操作

```bash
# 热重启 worker（零中断）
kill -HUP 545162
sleep 2

# 验证
curl -s --max-time 10 http://127.0.0.1:8080/ | head -c 500
# → HTTP 200, 29108 bytes, 内容正常
```

### 进程运行时长

| 服务 | 启动时间 | 运行时长 |
|------|---------|---------|
| gaofang-v2-fusion | 2026-05-12 21:02 | 2天11小时 |
| nginx | 2026-05-06 23:12 | 8天9小时 |
| postgresql | 2026-04-24 06:59 | 21天 |

## 教训总结

1. **只 `ss` 看到端口就下结论"服务正常"是错误的** — 端口在监听不代表 worker 能处理请求
2. **必须用 `curl` 本地测试**才能真正确认 gunicorn 是否响应
3. **gunicorn 默认无 `--max-requests`**，worker 生命周期无限是事故隐患
4. **`kill -HUP` 是零中断热重启**，远好于 `systemctl restart`
5. **Nginx 状态码模式**：304+499+504 序列 = 典型的 gunicorn 卡死模式
