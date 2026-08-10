---
name: flask-production-pitfalls
description: Flask/Gunicorn/PostgreSQL 生产环境常见故障模式 — 多 worker 并发写库竞态(UPSERT+文件锁)、静态缓存(cache-busting)、游客模式 401、前后端 ID 不匹配、500 返回 HTML 的诊断线索
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [flask, gunicorn, postgresql, production, concurrency, cache, troubleshooting]
    related_skills: [flask-api-troubleshooting, flask-mobile-pwa, systematic-debugging]
---

# Flask 生产环境常见故障模式

## Overview

Flask + Gunicorn（多 worker）+ PostgreSQL 部署后反复出现的**故障模式**与修复套路。开发环境测不出、一上线就踩的坑，集中在这里。每个模式给出：症状 → 根因 → 修复 → 验证。

**核心原则**: 生产环境的"前端报错"往往是后端/基础设施问题的表象，先验证后端再怀疑前端。

---

## When to Use

- 前端报 `Unexpected token '<'`、`加载失败`、`获取用户信息失败`，但接口 curl 显示 200
- 并发访问（多 worker）时接口偶发/全部 500，日志出现 `UniqueViolation`
- 改了后端/前端代码，用户仍看到旧行为（缓存问题）
- 表单编辑/创建报错，接口日志却 200 正常

---

## Pattern 1: Gunicorn 多 worker 并发写库竞态 → PostgreSQL UPSERT

**Symptom**: GET 列表接口偶发 500 `duplicate key value violates unique constraint`；并发压测（20 并发）全部失败/超时。前端表现为 `Unexpected token '<'`（500 返回 HTML）。

**Root Cause**: **check-then-insert 竞态**：多 worker 同时执行「查询→不存在→INSERT」同一唯一键。gunicorn `--workers 4 --threads 4` = 16 并发，先 commit 的赢，其余撞唯一约束。

**Fix（三层）**:

1. **PostgreSQL 原生 UPSERT**（数据库级原子操作，并发安全）：
```python
from sqlalchemy import text
upsert_sql = text("""
    INSERT INTO follow_up_records
        (patient_name, gender, age, month, ...)
    VALUES
        (:patient_name, :gender, :age, :month, ...)
    ON CONFLICT (patient_name, gender, age, month)   -- 唯一约束列
    DO UPDATE SET
        -- 只更新"计划/快照"字段
        pickup_date = EXCLUDED.pickup_date,
        updated_at = now()
        -- ⚠️ 绝不更新"状态"字段：已复诊状态/停服标记必须保留
""")
session.execute(upsert_sql, params)
```
> ⚠️ **SQLAlchemy 1.3 没有 `on_conflict_do_update`**（1.4+ 才有），必须用 `text()` 原生 SQL。新建表后要给应用用户 GRANT（用 postgres 建的表默认无权限）。

2. **节流 + 跨进程文件锁**（GET 接口以只读为主，写库限流）：
```python
import fcntl, time
SYNC_INTERVAL = 300  # 5分钟，时间戳节流
# fcntl.flock(lock_f, LOCK_EX | LOCK_NB)：跨进程互斥；拿不到锁就跳过（别的 worker 在同步）
# 注意：flock 按进程生效——gunicorn 多进程有效；同进程多线程需配合时间戳节流
```

3. **单事务批量提交**（性能关键，146s → 3.7s）：
- ❌ 每行/每患者一次 `commit()`（1596 次 fsync）
- ✅ 全部 UPSERT 后一次 `commit()`；再配合只读查询 → 0.06s
- ⚠️ 批量循环内不要查询（会触发 autoflush 把全部 pending flush，反而更慢）

**Verification**: 并发压测（20 个 curl 同时打接口），全部 200 JSON 才算过。

---

## Pattern 2: 前端 "Unexpected token '<'" → 后端返回了 HTML 而非 JSON

**Symptom**: PWA/前端报 `Unexpected token '<', "..."`，curl 接口却 200。

**Root Cause**: 请求返回了 **HTML**（`res.json()` 解析第一字符 `<` 失败）：
- **Flask 生产模式（DEBUG=False）未捕获异常 → 默认 500 HTML 错误页**（`jsonify` 只在 try/except 捕获时返回 JSON）
- **catch-all 路由** `@app.route('/<path:path>')` 把未匹配 API 路径（如 `/api/xxx/undefined`）转成 404 HTML

**Debug**:
1. 批量检查所有 API 的 Content-Type（不是只看状态码）：
```python
for p in paths:
    r = client.get(p, headers=h)
    ct = r.headers.get('Content-Type', '')
    print(f'{"❌" if "json" not in ct else "✅"} {p} -> {r.status_code} | {ct}')
```
2. 检查 app.py catch-all 路由；3. 查 gunicorn-error.log 的未捕获 traceback。

**Fix**: 所有 handler 用 try/except 包裹返回 `jsonify({"error": ...}), 500`；catch-all 对 `/api/` 前缀返回 JSON 404。

---

## Pattern 3: Nginx `expires 7d + immutable` 静态缓存 → cache-busting

**Symptom**: 后端接口返回新字段（curl 有值），前端仍显示旧数据/空值；用户 F5 也没用。

**Root Cause**: Nginx `/static/` 强缓存（与 PWA Service Worker 是**两层独立缓存**，都要排查）：
```nginx
location /static/ {
    expires 7d;
    add_header Cache-Control "public, immutable";
}
```
**症状迷惑点**: 字段名没变的列能显示，字段名变了的列显示空（旧 JS 读旧字段名，如 quantity → total_quantity）。

**Fix（cache-busting，不动 Nginx）**:
1. 动态加载脚本加时间戳：`script.src = '/static/js/page-' + name + '.js?v=' + Date.now();`
2. 静态 HTML 引用加版本号：`<script src="/static/js/common.js?v=20260803">`
3. PWA SW: bump `CACHE_NAME`；JS/CSS 改 network-first
4. 告知用户 **Ctrl+F5**
5. 验证：`curl -I /static/js/xxx.js` 看响应头

---

## Pattern 4: JS getElementById ID 与 HTML 不匹配 → null.value TypeError

**Symptom**: 点击编辑报「获取用户信息失败」/「创建失败」，实际错误 `Cannot set properties of null (setting 'value')`。**接口日志全部 200**——问题纯在前端。

**Root Cause**: JS 引用的元素 ID 与 HTML 模板不一致（如 `edit-username` vs 实际 `edit-user-username`），`getElementById` 返回 null。

**Debug（正则对比，秒定位）**:
```python
import re
html = open('templates/admin-users.html').read()
js = open('static/js/page-admin-users.js').read()
html_ids = set(re.findall(r'id="([^"]+)"', html))
js_ids = set(re.findall(r"getElementById\('([^']+)'\)", js))
print([i for i in sorted(js_ids) if i not in html_ids])  # → 不匹配清单
```

**Prevention**: 表单 ID 统一前缀（`edit-user-username` 类）；改完跑对比脚本；赋值前判断元素存在。

---

## Pattern 5: 统计数字基于「筛选后列表」→ 恒为 0 或不准

**Symptom**: tab 筛选（后端只返回待复诊）后，前端在返回数据上统计"已复诊 X 人"→ 已复诊的人不在返回里 → 恒为 0。

**Fix**: **一次拉全量**（不带筛选参数，limit 设 5000），前端本地按 tab 过滤列表 + **基于全量统计** 待/已/共 三个数字。数据量可控（几百条/几百 KB）时优先全量。

---

## Pattern 6: 未登录（游客）访问被 401 拦截 → 前端需自动 guest-login

**Symptom**: 未登录打开首页（如膏方记录页）显示"加载失败，请重试: 网络请求失败: 401"，登录后一切正常。用户期望**不登录也能看"未取"列表**。

**Root Cause**: 系统设计了游客模式（`/api/auth/guest-login` 返回 roles=['guest'] 的 token；后端 `_check_guest_role()` 对 guest 只返回 `status=='未取'` 记录且 `_mask_sensitive_fields()` 隐藏医生/剂型），移动端 PWA 已实现（登录页"游客登录(仅查看未取)"按钮），但 **PC 端某些页面未登录时直接无 token fetch**，被 `@auth_required` 在入口硬拦成 401。

**Fix**: PC 端未登录时先自动调 guest-login 拿 token，再带 `Bearer` 请求；登录用户逻辑不变：
```javascript
const fetchPrescriptions = authToken
    ? Promise.resolve(authToken).then(requestWithToken)
    : fetch(window.app.API_BASE_URL + '/auth/guest-login', { method: 'POST', headers: { 'Content-Type': 'application/json' } })
        .then(r => r.json())
        .then(data => {
            if (!data.token) throw new Error(data.error || '游客登录失败');
            return requestWithToken(data.token);
        });
```

**Verification**（curl 直接验证后端游客路径）:
```bash
GUEST_TOKEN=$(curl -s -X POST http://127.0.0.1:8080/api/auth/guest-login -H "Content-Type: application/json" | python3 -c "import sys,json;print(json.load(sys.stdin)['token'])")
curl -s "http://127.0.0.1:8080/api/prescriptions?status=未取" -H "Authorization: Bearer $GUEST_TOKEN" -w "HTTP %{http_code}\n"
# 应 200，且 doctor / prescription_type 为 null（敏感字段已隐藏）
```

**Key insight**: 后端已支持游客 ≠ 前端自动用游客模式。排查 401 前先问：这个页面是否本来就该未登录可看？若是，找 guest-login 流程（移动端 api.js 是参照实现）。

## Pattern 7: 缓存旧 JS 跳转已删路径 → 顽固 404（cache-busting 进阶）

**Symptom**: 改 JS 后用户仍看到旧行为——甚至**跳转到已删除的路径**（如 `/api/login` GET 404，`{"error":"请求的资源不存在"}`），强刷 F5 也没用。磁盘代码明明已改对。

**Root Cause**: Pattern 3 的延伸——**index.html 直接引用的静态脚本若没版本号**，会被 Nginx `expires 7d + immutable` 缓存 7 天。浏览器一直执行旧 JS（含旧的跳转/旧字段名）。common.js 动态加载的页面脚本带 `?v=Date.now()` 不受影响，但 index.html 里 `<script src>` 直引的没有。

**Debug 线索**: 用户报的路径/行为与磁盘代码不符 → 先 `curl -s http://host/ | grep -o 'xxx[^"]*'` 确认 index.html 是否已带新版本号，再 curl 带版本号的 JS 确认内容。

**Fix**: 改完静态 JS 后**必须同步升 index.html 里对应 script 标签的版本号**：
```html
<!-- 改前 -->
<script src="/static/js/page-prescriptions.js"></script>
<!-- 改后 -->
<script src="/static/js/page-prescriptions.js?v=20260807"></script>
```
光靠用户 Ctrl+F5 对 immutable 缓存不一定生效——version-bump 是唯一可靠兜底。

## Pattern 8: 登录后 localStorage.permissions 永远为空 → 权限门控字段全员 disabled

**Symptom**: 编辑弹窗里某些字段（如剂型、医生）**所有用户都置灰**——连应该可编辑的药局管理员也不行。数据库里角色明明有对应权限点（`prescription_type:view` / `doctor:view`），后端 PUT 也放行，但前端就是灰的。

**Root Cause**: 登录成功后的**异步竞态**——`fetch('/api/auth/me')` 异步拉权限写 `localStorage.permissions`，但紧接着同步代码里 `window.location.reload()` **立即刷新页面**，fetch 还没 resolve 页面就 reload 了 → 权限永远写不进 localStorage → `checkPermission()` 恒 false → `disabled = !canViewType` 恒 true。

**Debug 线索**: 浏览器 console 查 `localStorage.getItem('permissions')` 是 `null`（而非 `[...]`）；但手动 `fetch('/api/auth/me')` 返回的 permissions 数组完整。**先怀疑登录写入时序，不要怀疑后端/装饰器/权限点**。

**Fix**: 权限拉取完成后（或超时兜底）再刷新：
```javascript
var permissionFetch = fetch('/api/auth/me', { headers: {'Authorization': 'Bearer ' + data.token} })
    .then(r => r.json())
    .then(me => {
        var perms = [];
        if (me && me.permissions) perms = me.permissions.map(p => p.name || p);
        localStorage.setItem('permissions', JSON.stringify(perms));
    })
    .catch(() => localStorage.setItem('permissions', '[]'));
var permissionTimeout = new Promise(resolve => setTimeout(resolve, 3000));
Promise.all([permissionFetch, permissionTimeout]).then(() => {
    // hide modal; updateLoginStatus(); window.location.reload();
});
```

**⚠️ 改 common.js 后必须同步升 index.html 的版本号**（Pattern 7）：`common.js?v=20260803` → `?v=20260807b`，否则 immutable 缓存让修复不上线。

**Verification**: 登录后 console 查 `localStorage.getItem('permissions')` 含目标权限点；打开编辑弹窗查 `document.getElementById('edit-prescription-type').disabled === false`。

**Key insight**: 「所有角色都不能编辑」几乎从不是权限配置问题——是**权限数据根本没加载到前端**。后端权限点存在 + 前端 checkPermission 恒 false = 登录写入链路的 bug。

---

## Pattern 9: 任意文件下载漏洞 — static_folder 指向项目根目录（高危）

**Symptom**: 巡检时 curl 探测敏感路径全部返回 200：
```bash
curl -s http://host/.env                    # 200 → DB 密码泄露！
curl -s http://host/config.py               # 200 → 源码+密钥配置
curl -s http://host/api/v1/auth.py          # 200 → JWT 认证逻辑
curl -s http://host/logs/gunicorn-error.log # 200 → 日志泄露
```
前端页面正常、API 正常，攻击面藏在**静态文件服务路由**里。

**Root Cause（两个条件叠加）**:
```python
# ① static_folder 指向项目根目录（而非 static/ 子目录）
static_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)))
# ② catch-all 路由 + send_from_directory(static_folder, path)
@app.route('/<path:path>')
def serve_other_static(path):
    return send_from_directory(static_folder, path)
```
`send_from_directory` 会 URL 解码并防路径穿越，但**不限制目录内容**——目录指向项目根，`.env`/`*.py`/`logs/*.log` 全部可下载。

**二次危害 — 默认 JWT 密钥回退**:
`.env` 未设 `SECRET_KEY`/`JWT_SECRET_KEY` 时 config.py 回退到硬编码默认值（如 `'dev-jwt-secret-change-in-production'`）。该默认值随 config.py 泄露后，**攻击者可伪造任意用户 JWT（含 super_admin）登录系统**——比 DB 密码泄露更严重。

**Debug 线索**: 先确认 200 来自谁——Nginx `location /` 是 proxy_pass 时，200 响应来自 **Flask 而非 Nginx**，别只查 Nginx 配置。找 app.py 里的 `static_folder =` 赋值行即可定位。

**Fix（三层）**:
1. **Nginx 立即止血**（不重启应用）:
```nginx
location ~* \.(env|py|log|cfg|ini|bak|old|swp|sqlite|db)$ {
    deny all;
    return 404;
}
```
2. **Flask 根治**: `static_folder` 改指 `static/` 子目录；catch-all 白名单化或移除。
3. **凭据轮换**（泄露过就必须换）: `.env` 生成强随机 `SECRET_KEY`/`JWT_SECRET_KEY`（`openssl rand -hex 32`）+ 轮换 DB 密码 + 重启 Gunicorn。

**Verification**: 修复后重跑探测命令，`/.env`、`/config.py`、`/app.py`、`/auth.py`、`/logs/*.log` 应全部 404。

> ⚠️ 巡检/健康检查时应**主动**跑敏感文件探测（`.env` `config.py` `app.py` `auth.py` `.git/config` `logs/*.log`），期望全 404。参考 `server-health-monitor` 的 Step 6（该技能未含此步时，以本 Pattern 为准）。

---

## 完整案例

膏方管理系统复诊模块 2026-08 改版完整过程（时段规则、UPSERT SQL 细节、压测数据、缓存修复链）见 `references/followup-module-overhaul-2026-08.md`。

## References

- 任意文件下载漏洞完整诊断实录（膏方 V2, 2026-08-10）: `references/arbitrary-file-download-gaofang-2026-08-10.md`
- PostgreSQL ON CONFLICT: https://www.postgresql.org/docs/current/sql-insert.html
- Gunicorn workers/threads: https://docs.gunicorn.org/en/stable/design.html
