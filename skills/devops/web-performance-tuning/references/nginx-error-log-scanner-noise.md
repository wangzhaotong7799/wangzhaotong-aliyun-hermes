# Nginx 错误日志：区分真正错误与扫描器噪音

当用户反馈「修复网站的错误」时，不要只看 Nginx 错误日志就下结论。大量 404/403 是外部扫描器/爬虫的试探请求。

---

## 判断流程

### 第1步：谁在请求？

```bash
# 查看最近错误日志，提取 IP 和请求路径
tail -50 /www/wwwlogs/xxx_error.log

# 常见扫描器特征 IP 段
# 119.91.x.x, 112.121.x.x — 阿里云扫描器/爬虫
```

**IP 筛查：** 如果请求 IP 是公有云/机房段（阿里云、腾讯云、华为云等），90% 是扫描器，不是真实用户。

### 第2步：请求的域名是什么？

查看 Nginx 错误日志中的 `client:` 和 `host:` 字段：

```
client: 119.91.140.33, server: _, request: "...", host: "byw-841007.hichina.com"
```

- `server: _` = 匹配的是默认 server，没有 server_name 匹配
- `host: "byw-841007.hichina.com"` = 外部未知域名指向你的 IP
- **扫描器特征：** 通过不在名单里的域名或直接 IP 访问

### 第3步：文件真的被引用了？

```bash
# 查找 HTML 模板中是否引用这些 JS/CSS 文件
grep -r 'chart\.js\|xlsx\.js\|response\.js\|r\.js' templates/ static/*.html 2>/dev/null
```

| 日志报错文件 | 实际引用文件 | 判断 |
|---|---|---|
| `chart.js` (小写) | `chart.umd.min.js` | ❌ 扫描器 |
| `Chart.js` (大写C) | `chart.umd.min.js` | ❌ 扫描器 |
| `xlsx.js` | `xlsx.full.min.js` | ❌ 扫描器 |
| `XLSX.utils.js` | 不存在 | ❌ 扫描器 |
| `r.js` | 不存在 | ❌ 扫描器 |
| `response.js` | 不存在 | ❌ 扫描器 |

### 第4步：浏览器实际验证

```bash
# 打开浏览器访问网站
browser_navigate(url="http://127.0.0.1/")

# 检查浏览器控制台是否有 JS 报错
browser_console()

# 检查是否有 HTTP 4xx/5xx 资源
# 在浏览器中执行:
browser_console(expression="window.performance.getEntriesByType('resource').filter(r => r.responseStatus >= 400).map(r => r.name + ' → ' + r.responseStatus)")
```

---

## 扫描器常见请求模式

扫描器会试探常见的安全漏洞路径：

| 试探路径 | 说明 |
|---|---|
| `/.env` | 环境变量泄露 |
| `/.git/config` | Git 信息泄露 |
| `/dockerfile`, `/docker-compose.yaml` | Docker 配置泄露 |
| `/phpinfo.php`, `/test.php` | PHP 探针（非 PHP 服务器也会被扫） |
| `/main.go`, `/server.go` | Go 源码试探 |
| `/claude.md`, `/CLAUDE.MD` | AI Agent 配置文件试探 |
| `/api.json`, `/api/geojson` | API 路径枚举 |
| 同名大小写变体 | `chart.js` vs `Chart.js` vs `chart.umd.min.js` |

**这些请求 100% 是扫描器**，与网站功能无关。

---

## 真正的网站错误特征

需要认真对待的错误日志：

| 错误类型 | 例子 | 严重程度 |
|---|---|---|
| `upstream timed out (110:)` | `/` 或 API 超时 | 🚨 需排查 Gunicorn 卡死 |
| `connect() failed (111:)` | 无法连接后端端口 | 🚨 服务宕机 |
| `recv() failed (104:)` | 连接被对端重置 | ⚠️ 可能网络或请求异常 |
| `open() "(real template path)" failed` | CSS/JS 在 HTML 中有引用但磁盘缺失 | ⚠️ 需修复静态文件 |
| `Permission denied (13:)` | Nginx 临时目录权限不足 | 🚨 功能异常 |

**判断标准：** 确认 HTML 模板中有引用 → 才是真实错误。

---

## 关于 favicon.ico 404

浏览器自动请求 `/favicon.ico`，如果项目没有放这个文件，所有页面访问都会产生一条 404。

**修复（可选）：**
```bash
# 找一个图标放到项目 static/ 目录
# 或用简单方法——在 HTML <head> 中设置空图标
# <link rel="icon" href="data:,">
```

不影响功能，但日志里会一直出现。

---

## 参考场景：本次排障记录

**问题：** 用户反馈「修复网站的提示的错误」

**初始发现：** Nginx 错误日志显示缺失 JS 文件 — `chart.js`, `Chart.js`, `xlsx.js`, `XLSX.utils.js`, `r.js`, `response.js`

**实际结论：**
1. HTML 模板引用的是 `chart.umd.min.js`, `xlsx.full.min.js` — 全部存在 ✅
2. 请求来自 IP `119.91.140.33`，通过域名 `byw-841007.hichina.com` — 扫描器
3. 浏览器访问页面零 JS 报错
4. 网站实际运行正常 ✅

**教训：** 不要被 Nginx 错误日志中的扫描器噪音误导。先验证 HTML 模板引用。
