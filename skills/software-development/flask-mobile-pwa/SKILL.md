---
name: flask-mobile-pwa
description: "为现有 Flask API 后端添加独立移动端 PWA — 零后端改动，独立 /mobile/ 目录，聚焦核心模块"
version: 1.0.0
author: Hermes Agent
metadata:
  hermes:
    tags: [flask, pwa, mobile, frontend]
    related_skills: [flask-web-preload-lazy-load, plan]
---

# Flask 移动端 PWA 添加指南

## 适用场景

为已有 Flask API 后端系统（桌面 SPA）添加手机端 PWA 入口，**不修改现有代码**，**最小化后端改动**。

## 核心原则

### 1. 独立目录结构

```
static/mobile/      ← 全新的移动端目录，与现有前端完全隔离
  ├── index.html    ← PWA 入口（含 manifest 链接）
  ├── manifest.json ← PWA 安装清单
  ├── sw.js         ← Service Worker
  ├── css/app.css   ← 移动端样式
  └── js/
      ├── api.js        ← API 封装（JWT 注入）
      ├── router.js     ← 前端 hash 路由
      ├── store.js      ← 本地状态（token、用户信息）
      ├── page-login.js ← 登录页
      ├── page-*.js     ← 各功能页面
```

### 2. 后端改动最小化

```
仅需:
  ├── pip install flask-cors          ← 跨域支持
  ├── app.py: CORS(app)               ← 启用 CORS
  └── app.py: 新增路由 /mobile/<path>  → static/mobile/
  
  零逻辑改动，现有 API 直接复用。
```

### 3. 用户权限继承

PWA 登录后复用同一套 JWT + RBAC 权限系统。医助角色自动应用 `_apply_assistant_filter` 数据过滤。

---

## 实施流程

### 第一步：确定范围

必须回答的 5 个问题：

| 问题 | 作用 |
|------|------|
| 谁用？ | 医助/药局/医生/管理员 → 决定功能集 |
| 做什么？ | 列出最高频的 2~3 个核心操作 |
| 不做什么？ | 显式排除 → 避免范围蔓延 |
| 用不用 HTTPS？ | 影响 PWA 安装和 iOS 兼容性 |
| 要拍照/扫码吗？ | 影响技术选型（浏览器 JS vs 原生插件） |

### 第二步：设计页面

**3 页模式（最常用）：**

| 页面 | 核心操作 | 对应 API |
|------|---------|----------|
| 列表页（查询） | 搜索、筛选、查看状态 | `GET /api/...` |
| 操作页（更新） | 状态流转、标记完成 | `POST /api/...` |
| 提醒页（时间线） | 查看到期项、标记处理 | `GET + POST /api/...` |

### 第三步：数据流

```javascript
手机浏览器 → /mobile/index.html
  → api.js 注入 JWT token（localStorage 持久化）
  → 调用现有 API（flask-cors 支持跨域）
  → 渲染移动端卡片 UI
```

### 第四步（关键）：API 分页

**移动端必须加分页。** 桌面端可以一次加载几百条数据，手机浏览器会直接卡死。

```javascript
// ❌ 错误：没有分页 → 加载全部数据（手机卡死）
Api.getPrescriptions({});

// ✅ 正确：每页 50 条，底部「加载更多」
Api.getPrescriptions({ page: 1, per_page: 50 });
```

在移动端 PWA 中，每个列表页都应默认分页：

| 字段 | 推荐值 | 说明 |
|------|--------|------|
| `per_page` | 20~50 | 手机屏幕一次看到 3~5 张卡片，50 条需要 2~3 屏 |
| `page` | 递增 | 从 1 开始，加载更多时 +1 |
| 加载更多按钮 | 列表底部 | 不要自动无限滚动（移动端触摸容易误触） |

### 第五步（推荐）：时间范围过滤

限制 API 返回的数据在合理时间范围内：

```javascript
// 只查最近 6 个月的数据
var sixMonthsAgo = new Date();
sixMonthsAgo.setMonth(sixMonthsAgo.getMonth() - 6);
var startDate = sixMonthsAgo.toISOString().split('T')[0];

Api.getPrescriptions({ page: 1, per_page: 50, start_date: startDate });
```

**为什么需要？**
- 手机端不需要查几年前的历史数据
- 减少 API 返回数据量（从 660 条降到 221 条）
- 减少分页页数（从 14 页降到 5 页）
- 提升首次加载速度

### 第四步：PWA 安装

```json
// manifest.json 必需字段
{
  "name": "应用名称",
  "short_name": "简称",
  "start_url": "/mobile/",
  "display": "standalone",
  "background_color": "#ffffff",
  "theme_color": "#0d6efd",
  "icons": [{ "src": "/mobile/icon-192.png", "sizes": "192x192", "type": "image/png" }]
}
```

---

## 范围决策模式

记录了一个典型决策路径（来自膏方管理系统 V2）：

```
用户说 "写一个手机APP"               → 假设广泛
用户说 "主要是给医助用"               → 收窄角色
用户说 "膏方领取，复诊，提醒3块就行"   → 收窄功能
用户说 "PWA，不用拍照上传和HTTPS"     → 确定技术方案
```

**每轮收窄都将后续工作量减半。**

---

## 常见问题

### Q: 为什么用独立 /mobile/ 目录而不改现有 SPA？
A: 零冲突。现有桌面 SPA 的复杂逻辑（7 个标签页、管理员功能、打印、Excel）不需要移植。手机端只用 3 个核心页面，重写比改造快。

### Q: 不搞 HTTPS 有问题吗？
A: PWA 的 Service Worker 注册需要 HTTPS 或 localhost。纯 HTTP 环境下 PWA 的核心功能（离线缓存、后台同步）不可用，但基本页面访问和 API 调用不受影响。

### Q: 前端用什么 UI 框架？
A: 建议手写轻量 CSS（移动端适配）或 Bootstrap 5 的移动端组件。不要引入 React/Vue 等重型框架 — PWA 的各页面 JS 文件独立，用原生 JS 足够。

---

## 常见陷阱

### 陷阱 1：Flask 路由顺序 — `/<path:path>` 截胡 `/mobile/`

**问题：** Flask 的 `@app.route('/<path:path>')` 是贪婪匹配，任何未被其他路由匹配的路径（包括 `/mobile/`）都会被它截胡，导致新增的 mobile 路由返回 404。

**表现：** `curl http://localhost:8080/mobile/` 返回 404，但 `curl http://localhost:8080/static/mobile/index.html` 正常（`/static/<path>` 路由先注册）。

**修复：** 将 `/mobile/` 路由注册在 `/<path:path>` 之前：

```python
# ✅ 正确：手机路由放在前面
@app.route('/mobile/')
@app.route('/mobile/<path:path>')
def serve_mobile(path='index.html'):
    return send_from_directory('static/mobile', path)

# ❌ 错误：catch-all 路由放在手机路由前面
@app.route('/<path:path>')
def serve_other_static(path):
    return send_from_directory(static_folder, path)
```

**原理：** Flask 按路由注册顺序匹配，`/<path:path>` 匹配一切路径，先注册先服务。

### 陷阱 2：隐藏的 gunicorn 进程

**问题：** 服务器上可能存在之前用 gunicorn 启动的旧进程（可能还是 Python 3.6），它默默占着端口。新起的 Flask dev server 因为端口被占用静默退出，导致怀疑"代码没生效"。

**表现：**
- `ps aux | grep gunicorn` 发现旧进程
- `ss -tlnp | grep 8080` 显示 gunicorn 占着端口
- 修改了代码但重启后 404 — 因为旧 gunicorn 没重新加载

**排查方法：**
```bash
# 检查谁占着端口
ss -tlnp | grep 8080

# 检查所有相关进程
ps aux | grep -E 'gunicorn|app.py' | grep -v grep

# 强制清理后再启动
pkill -f gunicorn 2>/dev/null
pkill -f 'python3.8 app.py' 2>/dev/null
```

**修复：** 生产环境不要混用 Flask dev server 和 gunicorn。统一用一种方式启动。

**补充：崩溃循环（Restart Loop）**

当 gunicorn 被 OOM 或 SIGKILL 强行杀死时，端口可能被旧的 master 进程僵尸占用，systemd 自动重启新进程会反复失败：

```
systemd: Starting gunicorn...
gunicorn: Connection in use: ('0.0.0.0', 8080)
gunicorn: Can't connect to ('0.0.0.0', 8080) → exit code 1
systemd: restart (RestartSec=10s) → ... 循环 35 次
```

**解决方案：**
1. 在 gunicorn 命令行加 `--reuse-port`（启用 SO_REUSEPORT，新进程可绑定半残留的端口）
2. 降低 `RestartSec` 减少风暴持续时间
3. 检查 syslog `dmesg | grep oom` 确认 OOM 根因

```bash
# 检查是否 OOM 引起的
dmesg | grep -i "oom\|killed" | tail -5

# 查看崩溃循环次数
journalctl -u your-service.service | grep -c "Started.*Service"
```

### 陷阱 3：Flask dev server 还是 gunicorn？

**问题：** PWA 开发阶段用 `app.run()` 没问题，但部署到生产环境（多位医助同时访问）需要用 gunicorn。

| 方式 | 适用场景 | 并发能力 |
|------|---------|---------|
| `python3 app.py` | 开发测试 | 单线程，调试模式方便 |
| `gunicorn app:app -w 2 -t 120` | 生产部署 | 多 worker，支持并发 |

**启动命令：**
```bash
# 开发
cd /path/to/project && python3 app.py

# 生产
cd /path/to/project && gunicorn --bind 0.0.0.0:8080 --workers 2 --threads 2 --timeout 120 app:app
```

### 陷阱 4：Flask test client 返回 200 但真实服务 404

当 `app.test_client().get('/mobile/')` 返回 200 但 `curl http://localhost:8080/mobile/` 返回 404 时，**问题不在代码而在运行中的服务进程**。test_client 总是用最新的代码，而运行中的服务可能是旧代码（见陷阱 2）。

记住这个诊断原则：**test_client ✅ + 真实请求 ❌ = 服务进程问题，不是代码问题。**

### 陷阱 6：JavaScript 字符串拼接 + 链式调用断裂

**问题：** PWA 页面使用 JS 字符串拼接（`'...' + '...'` 模式）渲染 HTML，当在行首使用 `+` 号时，会意外截断链式方法调用。

**典型错误：**

```javascript
// ❌ 错误：行首 + 号把 .filter().map().join('') 链式调用截断了
listEl.innerHTML = fields
  .filter(function(f) { return f[1]; })      // ✅ filter 正常
+   .map(function(f) {                       // ❌ + 号让 .map 变成了字符串拼接！
+     return '<div>' + f[0] + '</div>';
+   })
+ '</div>';

// ✅ 正确：不要在链式调用中使用 + 号
var filtered = fields.filter(function(f) { return f[1]; });
var html = filtered.map(function(f) {
  return '<div>' + f[0] + '</div>';
}).join('');
listEl.innerHTML = html;

// ✅ 或者用 for 循环替代（本 PWA 推荐的方案）
var html = '';
for (var i = 0; i < fields.length; i++) {
  if (!fields[i][1]) continue;
  html += '<div>' + fields[i][0] + '<span>' + fields[i][1] + '</span></div>';
}
listEl.innerHTML = html;
```

**诊断方法：** 页面完全空白、控制台报 `Uncaught SyntaxError` 时，检查 IIFE 内部的字符串拼接行。特别是 `filter().map().join()` 链式调用前的 `+` 号。

**根因：** 行首的 `+` 号被 JS 解析为字符串拼接运算符（一元运算符优先级低于方法调用），导致 `.map` 不再作为链式调用的一部分。

**最佳实践：** 渲染复杂列表时，先用 `for` 循环或 `Array.map()` 分离计算好 HTML 字符串，最后一次性赋值给 `innerHTML`。不要在拼接语句中间插入链式方法调用。

### 陷阱 7：`\n\`（反斜杠换行）JS 字符串续行模式

**问题：** PWA 页面（特别是 page-reminders.js）使用反斜杠换行续行模式拼接长字符串：

```javascript
return '\n\
  <div class="card">\n\
    <div class="card-title">' + name + '</div>\n\
    <div class="card-row">\n\
      <span class="card-label">标签</span>\n\
      <span class="card-value">' + value + '</span>\n\
    </div>\n\
  </div>\n\
';
```

**为什么是陷阱：**

1. **难以批量修改：** 后续新增/删除一行时，必须同时调整前后行的续行反斜杠，很容易漏掉导致语法错误。
2. **patch 工具无法匹配：** 文件中的 `\n\`（反斜杠+新行）在不同编辑器中复制粘贴时容易变形，使用 `skill_manage(patch)` 时 old_string 很难找到精确匹配。
3. **语法检查不直观：** 漏掉末尾的反斜杠会静默截断字符串，JS 解析器报的错位置和真实问题位置不一致。

**推荐替换方案：** 使用数组 `join('')` 替代续行：

```javascript
// ✅ 更好的方式：数组 + join('')
return [
  '<div class="card">',
  '<div class="card-title">' + escapeHtml(item.patient_name || '') + '</div>',
  '<div class="card-row">',
  '<span class="card-label">标签</span>',
  '<span class="card-value">' + value + '</span>',
  '</div>',
  '</div>'
].join('');
```

**什么时候用续行模式还行：** 一次性写好不再改动的静态模板。如果预期未来会频繁调整字段，一开始就用数组 Join 模式。

### 陷阱 10：Service Worker 缓存导致静态文件更新不生效

**问题：** 更新了 `pinyin-util.js`、`page-pickup.js` 或其他前端文件后，用户刷新 PWA 但改动不生效。开发者用 curl 验证服务端文件已更新，但用户浏览器始终看到旧版本。

**根因：** Service Worker 的 `cache-first` 策略（`caches.match(event.request).then((cached) => cached || fetch(event.request))`）让浏览器**根本不发网络请求**，直接从本地缓存服务。即使服务端文件内容已变，用户也看不到新版本。

**修复方法：**

1. **更新 `sw.js` 的缓存版本号**（推荐 +1 递增）：
   ```javascript
   const CACHE_NAME = 'gaofang-mobile-v1';  // → v2 → v3
   ```
   activate 事件会自动清理旧版缓存。

2. **`sw.js` 自身禁止 HTTP 缓存**（参考 Flask 示例）：
   ```python
   if path.endswith('sw.js'):
       resp.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
   ```

3. **告知用户关闭 PWA 重新打开**（刷新页面不够，要完全关标签页）。

**防御措施：**
- 每次改前端文件，顺手检查 `sw.js` 版本号是否需递增
- 开发阶段可临时在浏览器中 Unregister SW（DevTools → Application → Service Workers → Unregister）

**问题：** 当有 3 个 PWA 页面（pickup / followup / reminders）时，同一个字段（如「医助」「医生」「剂型」）需要在多个页面的卡片列表或弹窗中统一显示/隐藏。容易遗漏。

**典型场景：** 用户要求"医生和剂型隐藏，显示医助"→ 需要改：
- `page-pickup.js` 的卡片列表（`renderList` 内的 HTML 模板）
- `page-pickup.js` 的弹窗详情（`showDetail` 中的 fields 数组）
- `page-followup.js` 的卡片列表
- `page-reminders.js` 的卡片列表（使用 `\n\` 续行模式）

**原则：先 grep 再改。** 确认所有出现该字段的地方都一致更新了：

```bash
# 改之前先搜，确认涉及哪些文件和哪些位置
grep -n -i 'doctor\\|医生\\|assistant\\|医助\\|prescription_type\\|剂型' static/mobile/js/*.js
```

**建议：** 如果 3 个页面都用同一个字段列表配置模式（而非各自硬编码 HTML 模板），后续改字段只需要改一处。但本 PWA 架构中每个页面独立维护自己的卡片 HTML，所以改字段必须逐一排查。

---

---

### 陷阱 9：客户端过滤与分页不兼容

**问题：** PWA 从 API 拉取一页数据（如 50 条），然后在 JavaScript 端根据筛选标签（未取/已取/欠药）对这批数据做客户端过滤。这会导致：

- **已取数据永远不显示**：如果第一页（按 id DESC 排序的最新 50 条）全是「欠药」和「未取」，用客户端过滤永远找不到「已取」记录，因为已取数据都在更早的页面上。
- **未取数量不准确**：默认只加载第一页，未取数据只包含这一页内的，不是实际总数。
- **用户点「加载更多」累积了多页后，计数依然不对**：因为客户端只拿到了部分数据，全量数据需要几十次翻页。

**典型场景（膏方系统 V2 PWA）：**

数据库真实数据：未取 12 条，已取 3176 条，欠药 55 条  
PWA 第一页 API 返回（每页 50 条，按 id DESC）：欠药 47 条 + 未取 3 条，已取 0 条  
用户点「已取」筛选 → 客户端过滤 → 0 条匹配 → 显示「暂无处方记录」  
用户点「未取」筛选 → 显示 3 条（实际应有 12 条）

**根因分析：**
```
PWA 模式                    vs      正确模式（服务端过滤）
━━━━━━━━━━━━━━━━━━━━━━             ━━━━━━━━━━━━━━━━━━━━━━
API 返回第 1 页 50 条 (全部状态)    API 返回第 1 页 50 条 (已取)
客户端从 50 条中找「已取」→ 0 条   服务端从 3176 条中查 → 50 条
结果：「暂无处方记录」               结果：显示已有记录
```

**修复方案：**

```javascript
// ❌ 错误：客户端过滤 + 分页（默认加载第 1 页 50 条，然后客户端 filter）
Api.getPrescriptions({ page: 1, per_page: 50, start_date: startDate })
  .then(function(resp) {
    state.allData = resp.data;      // 只有 50 条
    // 然后客户端过滤 state.allData.filter(item => item.status === filter)
  });

// ✅ 正确：将 status 参数传给服务端，服务端过滤
function fetchPage(status, page) {
  var params = { page: page, per_page: 50, start_date: startDate };
  if (status && status !== '全部') {
    params.status = status;    // ← 关键：让服务端做筛选
  }
  Api.getPrescriptions(params).then(function(resp) {
    state.allData = state.allData.concat(resp.data);  // 全部是筛选后的结果
    renderList();   // 直接渲染，不需要再客户端过滤
  });
}

// 切换筛选标签时 → 重新从第 1 页加载（带上新的 status 参数）
function switchFilter(newFilter) {
  state.allData = [];
  state.page = 1;
  fetchPage(newFilter, 1);
}
```

**何时可以用客户端过滤？**
- 数据量很小且固定（几十条）且全部一次性加载完毕
- 数据不带 pagination，一次性返回全部

**何时必须用服务端过滤？**
- 数据量超过一页（几十条以上）
- 使用了分页加载（page + per_page）
- 筛选结果分布在不同页面上（如已取数据多数在早期页）

**诊断方法：**

```bash
# 1. 看 API 调用是否带了 status 参数
curl -s "http://localhost:8080/api/prescriptions?page=1&per_page=50" 2>/dev/null \
  | python3 -c "import json,sys; data=json.load(sys.stdin); s={}; [s.__setitem__(i.get('status','?'),s.get(i.get('status','?'),0)+1) for i in data.get('data',[])]; print(s)"

# 2. 对比带 status 参数的 API 调用
curl -s "http://localhost:8080/api/prescriptions?status=%E5%B7%B2%E5%8F%96&page=1&per_page=1" \
  | python3 -c "import json,sys; data=json.load(sys.stdin); print(f'已取 total={data.get(\"total\",\"?\")}')"
  
# 3. 如果两个 total 不一样 → 后端支持服务端过滤，前端应该用
```

**防御措施：**
- PWA 开发阶段，每个筛选标签都先问：这个筛选是客户端做还是服务端做？
- 默认优先服务端过滤（API 支持的话），客户端过滤只用于一次性全量数据的简单搜索
- 分页 + 筛选的组合场景，永远走服务端

### 陷阱 5：API 参数名/value 前后端不匹配

PWA 直接调用后端 API 时，极易踩坑的参数不匹配有 5 种：

#### 5a. 查询参数与后端自动过滤冲突

**问题：** 后端已有 `_apply_assistant_filter` 自动按 JWT 角色过滤医助数据，但前端又传了 `assistant=username` 参数，导致两个条件叠加（`AND` 而非 `OR`），数据被错误排除。

**典型场景：** 数据库中医助字段存的是空字符串 `""`，后端过滤器检查 `assistant == '' OR assistant == username`，但加上 `assistant=username` 参数后变为 `(assistant == '' OR assistant == username) AND (assistant == username)`，空字符串记录被排除。

```javascript
// ❌ 错误：前端自己传了 assistant 参数
Api.getPrescriptions({ assistant: user.username });

// ✅ 正确：让后端 JWT 自动过滤
Api.getPrescriptions({});
```

**原则：** 后端已有基于 JWT 的自动权限过滤时，前端不要重复传相同的过滤参数。

#### 5b. 状态值常量不匹配

**问题：** 后端 API 的状态过滤参数使用内部常量，但前端从桌面 SPA 抄来了不同命名。

```python
# 后端接受的值
follow_up_status: '待复诊', '已复诊', 'follow_up_1_pending', ...

# ⚠️ 前端传的值（错的）
follow_up_status: '待回访', '已完成'

# ✅ 前端应该传的值
follow_up_status: '待复诊', '已复诊'
```

**排查方法：** 用 curl 直接测试 API，对比前后端看的同一字段是否用了不同枚举值。

```bash
# 直接测 API 看返回了什么值
curl -s -H "Authorization: Bearer $TOKEN" "/api/follow-up?limit=1" | python3 -c "import sys,json; print(json.load(sys.stdin)[0].get('follow_up_status'))"
```

#### 5c. ID 字段名不匹配（patient_id vs prescription_id）

**问题：** 后端更新接口需要数据库主键 `patient_id`，但前端传了业务编码 `prescription_id`（代煎号），导致更新失败。

```javascript
// ❌ 错误：传了业务编码
Api.updateFollowup({ prescription_id: 'GJ202604...', status: '已打通', follow_up_number: 1 });

// ✅ 正确：传数据库主键
Api.updateFollowup({ patient_id: 1234, status: '已打通', follow_up_number: 1 });
```

**最佳实践：** 卡片元素同时存储两个 ID，发送请求时根据后端要求选择正确的：

```html
<div class="card" data-pid="{{ prescription_id }}" data-id="{{ id }}">
```

```javascript
function handleUpdate(prescriptionId) {
  var card = document.querySelector(`[data-pid="${prescriptionId}"]`);
  var patientId = card.getAttribute('data-id');
  Api.updateFollowup({ patient_id: parseInt(patientId), ... });
}
```

#### 5d. API 响应字段名与前端读取字段名不匹配

**问题：** 后端 API 返回的 JSON 字段名与前端 JS 读取的字段名不一致，导致状态标签始终显示默认值。

**典型场景：** 提醒页卡片的回访状态标签始终显示「未服药」，实际后端返回的是 `follow_up_status` 字段，但前端代码写的是 `item.reminder_status`。

```javascript
// ❌ 错误：前端读的字段名在 API 响应中不存在
var statusText = item.reminder_status || '未服药';  
// API 实际返回的是 follow_up_status，reminder_status 永远为 undefined

// ✅ 正确：前端字段名必须与 API 响应完全一致
var statusText = item.follow_up_status || '未服药';
```

**排查方法：**

```bash
# 1. 用 curl 直接看 API 返回了什么字段名
curl -s "http://localhost:8080/api/reminders?limit=1" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool | head -30

# 2. 对比前端 JS 中读取的字段名
grep -n 'item\.' static/mobile/js/page-*.js
```

**根因分析路径：**
1. 桌面 SPA 可能用了另一套字段名（`reminder_status`），但后端改版后字段已重命名为 `follow_up_status`
2. PWA 开发时从桌面 SPA 抄了代码但没验证 API 实际返回的字段
3. 或者开发时参照了旧版 API 文档，实际部署的 API 版本不同

**防御措施：**
- 每次 PWA 新页面开发时，先用 curl 摸清 API 响应结构再编码
- 字段名在 api.js 的接口方法里做一次映射（可选），或直接穿透后端原始字段名
- 状态值枚举（待回访/已回访/已停服）前后端保持同一个常量列表

#### 5e. 查询参数被后端忽略

**问题：** 前端传了筛选参数，但后端 API 从未读取该参数，导致所有筛选 tab 返回相同数据。

**典型场景：** 提醒页有「全部/未回访/已回访」三个 tab，前端发 `status=待回访`，后端函数体里从未调用 `request.args.get('status')`。

```python
# ❌ 错误：后端收到了参数但完全忽略
@followups_bp.route('/reminders', methods=['GET'])
def get_reminders():
    # ... 构建 result 列表 ...
    return jsonify(result)  # 始终返回全部数据，无视 ?status=xxx

# ✅ 正确：接收筛选参数并过滤
@followups_bp.route('/reminders', methods=['GET'])
def get_reminders():
    # ... 构建 result 列表 ...
    status_filter = request.args.get('status', '')
    if status_filter:
        result = [r for r in result if r.get('follow_up_status') == status_filter]
    return jsonify(result)
```

**排查方法：**

```bash
# 用 curl 分别测试带/不带参数的 API 响应，看结果是否一致
curl -s "http://localhost:8080/api/reminders" | python3 -c "import json,sys; d=json.load(sys.stdin); print(f'全部: {len(d)}')"
curl -s "http://localhost:8080/api/reminders?status=%E5%BE%85%E5%9B%9E%E8%AE%BF" | python3 -c "import json,sys; d=json.load(sys.stdin); print(f'待回访: {len(d)}')"
curl -s "http://localhost:8080/api/reminders?status=%E5%B7%B2%E5%9B%9E%E8%AE%BF" | python3 -c "import json,sys; d=json.load(sys.stdin); print(f'已回访: {len(d)}')"
# 如果三个结果一样 → 后端忽略参数
```

**防御措施：**
- 写后端 API 时，先拉出所有查询参数的列表再编码
- 前端传了参数但结果没变 → 优先怀疑后端没读取，而不是前端没发对

---

## 部署

### 生产环境启动

```bash
# 使用 gunicorn（推荐）
cd /path/to/project
source venv/bin/activate
gunicorn --bind 0.0.0.0:8080 --reuse-port --workers 2 --threads 2 --timeout 120 app:app
```

⚠️ **关键参数：`--reuse-port`**

如果没有这个参数，当 gunicorn 被 OOM Killer 杀死（或异常 SIGKILL）时，旧 master 进程可能来不及释放端口，systemd 重启新进程时会报 `Connection in use` → 退出 → systemd 再重启 → 反复循环（最多 35 次）。`--reuse-port` 启用 `SO_REUSEPORT` 套接字选项，新进程可立即绑定同一端口。**建议所有生产 gunicorn 实例都加上。**
# Nginx 反向代理（与桌面端共用）
# location /mobile/ {
#     proxy_pass http://127.0.0.1:8080/mobile/;
# }
```

### Python 版本兼容性

- Python 3.6：不推荐，很多新库不再支持
- Python 3.8+：建议，Flask 2.x + flask-cors 等依赖都能支持
- 切换 Python 版本后要重新创建 venv 并安装依赖

---

---

## 客户端过滤与服务端过滤陷阱

详见独立参考文档: `references/pwa-client-filter-vs-server-filter.md`

该文档覆盖以下场景：PWA 使用客户端过滤 + 分页加载时，筛选结果不准确（如「已取」数据永远不显示）。提供复现步骤、修复方案和防御措施。

---

## 详情弹窗内联编辑模式

详见独立参考文档: `references/inline-edit-pattern.md`

该文档覆盖以下场景的完整实现：

1. **角色控制编辑权限** — 只在特定角色/用户登录时显示编辑入口（如 `yizhu001`）
2. **三态切换** — 查看态/编辑态/保存中状态管理
3. **API 调用 + 本地状态同步** — 保存后更新 `state.allData[dataIdx]` 并重渲染卡片列表
4. **dataIdx 穿透传递** — 从卡片点击 → showDetail → saveBtn 回调的参数链

### 医助下拉编辑模式

详见独立参考文档: `references/assistant-edit-pattern.md`

## 数据合计数量栏

详见独立参考文档: `references/data-count-summary.md`

该文档覆盖以下场景的完整实现：PWA 列表页在筛选标签下方显示当前状态/搜索条件下的数据条数，包含服务端总数与本地过滤数的区分逻辑。

该文档覆盖「下拉框选择 + 新增输入」双模式编辑的完整实现：

1. **下拉框加载数据** — 从 `GET /api/assistants` 动态加载选项，当前值自动高亮
2. **双态切换** — 下拉选择模式 ↔ 自由输入模式（点击「+ 新增」切换）
3. **共享保存函数** — 两种模式共用一套保存逻辑，通过判断当前显示模式取对应按钮
4. **dataIdx 穿透** — 保存后同步 `state.allData[dataIdx]` 并重渲染卡片列表
5. **取消/返回恢复** — 取消回到初始态，返回时重新加载下拉列表（含新增项）

## 客户端搜索扩展

当需要在 PWA 的客户端搜索过滤中添加新字段时，三步完成：

### 拼音首字母模糊搜索

**需求**: 医助输入 `jsj` 即可搜索到「姜树杰」，无需完整输入汉字。

**推荐方案**: 轻量级本地字典映射（零外部依赖），详见 `references/pinyin-search.md`。

关键要点：
- 在 `index.html` 中先加载 `pinyin-util.js`，再加载页面模块
- **优先选择**：从数据库所有患者姓名字段中提取唯一字符，用后端 `pypinyin` 库批量生成映射（见生成脚本 `scripts/gen-pinyin-map.py`），覆盖度远高于手写字典
  - 最新版本支持**自动直连数据库**（`PGPASSWORD=xxx python3 gen-pinyin-map.py --write /path/to/pinyin-util.js`），无需手动粘贴
  - 运行后自动验证映射结果与已知患者姓名是否匹配
- 手写字典必然遗漏生僻字（如「姜」「树」不在常见字表里），导致搜索漏人 —— **一定要从数据库实际数据生成**
- 使用 `indexOf` 而非精确匹配，支持部分字母输入（如 `z` 匹配所有 z 开头的姓）
- 映射表只覆盖数据库中的汉字；如遇生僻字，可补充字典或回退后端 API
- **重要**：生成后必须验证。输入几个已知患者姓名（如「姜树华」）确认拼音首字母正确再部署。

### 第一步：修改搜索函数

```javascript
function renderList() {
  var filtered = state.allData.filter(function(item) {
    // ... 状态筛选 ...
    if (state.search) {
      var kw = state.search.toLowerCase();
      var name = (item.patient_name || '').toLowerCase();
      var id = (item.prescription_id || '').toLowerCase();
      var asst = (item.assistant || '').toLowerCase();   // ← 新增
      if (name.indexOf(kw) === -1 && id.indexOf(kw) === -1 && asst.indexOf(kw) === -1) {
        return false;
      }
    }
    return true;
  });
}
```

### 第二步：更新 placeholder 提示

```javascript
// 改之前
'<input placeholder="搜索患者姓名 / 代煎号">'
// 改之后
'<input placeholder="搜索患者姓名 / 代煎号 / 医助">'
```

### 第三步：确认 API 返回了该字段

```bash
# 用 curl 确认 assistant 字段在 API 响应中
curl -s "http://localhost:8080/api/prescriptions?limit=1" \
  -H "Authorization: Bearer $TOKEN" \
  | python3 -m json.tool | grep assistant
# 应返回 "assistant": "张医生" 这样的内容
```

## 验证清单

- [ ] 登录/注销流程完整
- [ ] JWT token 持久化（刷新页面不丢失登录态）
- [ ] API 调用正常（无 401/403/500）
- [ ] 医助数据过滤正确（只能看到自己名下数据）
- [ ] 底部导航栏切换正确
- [ ] 页面在不同手机尺寸上适配
- [ ] PWA 可安装（manifest.json 有效）
- [ ] 桌面端现有功能不受影响
- [ ] 没有隐藏的旧 gunicorn 进程占端口
- [ ] mobile 路由注册在 catch-all 前面
