---
name: flask-production-pitfalls
description: Flask/Gunicorn/PostgreSQL 生产环境常见故障模式 — 多 worker 并发写库竞态(UPSERT+文件锁)、静态缓存(cache-busting)、前后端 ID 不匹配、500 返回 HTML 的诊断线索
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

## 完整案例

膏方管理系统复诊模块 2026-08 改版完整过程（时段规则、UPSERT SQL 细节、压测数据、缓存修复链）见 `references/followup-module-overhaul-2026-08.md`。

## References

- PostgreSQL ON CONFLICT: https://www.postgresql.org/docs/current/sql-insert.html
- Gunicorn workers/threads: https://docs.gunicorn.org/en/stable/design.html
