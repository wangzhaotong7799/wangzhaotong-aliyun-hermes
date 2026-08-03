---
name: flask-gunicorn-concurrency
description: Flask + PostgreSQL + Gunicorn 多 worker 并发写库竞态排查与修复 — "Unexpected token '<'" 真凶、check-then-insert 唯一键冲突、UPSERT/节流锁/单事务批量提交模式
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [flask, gunicorn, postgresql, concurrency, upsert, unique-violation, troubleshooting]
    related_skills: [flask-api-troubleshooting, systematic-debugging]
---

# Flask + Gunicorn 并发写库竞态排查与修复

## When to Use

- 前端报 `加载失败: Unexpected token '<', "`（或其他 `Unexpected token '<'` JSON 解析错误）
- API 偶发 500，但单次 curl 测试全部 200 —— 并发才复现
- 列表/同步接口在 Gunicorn 多 worker（`--workers 4`）下偶发唯一键冲突（UniqueViolation）
- 接口"查询→没找到→INSERT"模式被多个 worker 同时执行

## 核心诊断签名

**`Unexpected token '<'` = 前端 `res.json()` 解析到了 HTML，不是 JSON。**

HTML 从哪来？最常见的是 **Flask 500 错误页**——由**未捕获异常**产生（`jsonify` 只覆盖 try/except 内的错误）。按此链路查：

```
前端报 Unexpected token '<'
  → 哪个请求返回了 HTML？（批量检查所有 /api/ 响应的 Content-Type）
  → gunicorn-error.log 里有 UniqueViolation / IntegrityError traceback 吗？
  → 是并发 check-then-insert 竞态（多 worker 同时 INSERT 同唯一键）
```

**⚠️ 不要先怀疑浏览器缓存。** "服务器 API 全 200" 的 curl 测试可能是运气好（命中不同 worker/时序）。并发压测才能复现。

## 排查步骤

1. **单请求验证**：curl 各 API，确认 200 + application/json（此时多半全过）
2. **并发压测复现**（bash 脚本，20 个 curl 后台并行）：
```bash
for i in $(seq 1 20); do
  ( CODE=$(curl -s -o /tmp/conc_$i.json -w "%{http_code}" "$URL")
    CT=$(head -c 1 /tmp/conc_$i.json)   # '[' = JSON 数组, '<' = HTML
    [ "$CODE" = "200" ] && [ "$CT" = "[" ] && echo OK || echo "FAIL $CODE $CT" ) &
done
wait
```
3. **看 gunicorn error log**：`UniqueViolation: duplicate key value violates unique constraint ...`
4. 检查接口是否每次请求都全量写库（GET 列表接口写库 = 设计缺陷，见下）

## 修复模式（三层）

### 1. 写库改 PostgreSQL 原生 UPSERT（并发安全、幂等）

SQLAlchemy 1.3 **没有** `on_conflict_do_update`（那是 1.4+），必须用原生 SQL：

```python
from sqlalchemy import text
upsert_sql = text("""
    INSERT INTO target_table (patient_name, ..., month, ...)
    VALUES (:patient_name, ..., :month, ...)
    ON CONFLICT (patient_name, ..., month)          -- 必须匹配唯一约束列
    DO UPDATE SET
        field1 = EXCLUDED.field1,                    -- 只更新"计划/快照"字段
        updated_at = now()
    -- ⚠️ 状态字段（已复诊/停服标记等）不要放进 SET —— 保留已录入数据
""")
session.execute(upsert_sql, params)
```

关键：`DO UPDATE SET` 只更新计划窗口/快照字段，**不碰状态字段**——并发下已录入状态也不丢失。

### 2. 节流 + 跨进程文件锁（只允许一个 worker 做全量同步）

Gunicorn workers 是独立进程，进程内锁无效，用 fcntl 文件锁：

```python
SYNC_STATE_FILE = '/tmp/sync_state'   # 记录上次同步时间戳
SYNC_LOCK_FILE = '/tmp/sync.lock'
SYNC_INTERVAL = 300                   # 5 分钟节流

def _maybe_sync(session):
    now = time.time()
    try:
        last = float(open(SYNC_STATE_FILE).read().strip() or 0)
    except Exception:
        last = 0
    if now - last < SYNC_INTERVAL:
        return False                     # 节流：直接跳过
    lock_f = open(SYNC_LOCK_FILE, 'w')
    try:
        fcntl.flock(lock_f, fcntl.LOCK_EX | fcntl.LOCK_NB)   # 非阻塞
    except OSError:
        return False                     # 其他进程正在同步
    try:
        _sync_all(session)
        open(SYNC_STATE_FILE, 'w').write(str(now))
    finally:
        fcntl.flock(lock_f, fcntl.LOCK_UN); lock_f.close()
```

### 3. 单事务批量提交（性能 146s → 0.06s）

- `_sync_records(..., commit=False)`：循环里只 `session.execute()`，不 commit
- 循环结束**一次** `session.commit()`
- ⚠️ 批量模式下**不要在循环里查询 ORM 对象**（`session.query()` 会触发 autoflush，把未提交的 UPSERT 全部 flush，反而更慢）
- 需要数据就最后统一查一次

## 接口架构原则

**GET 列表接口永远不要每次请求全量写库。** 正确模式：

```
请求 → _maybe_sync()（节流+锁，写）→ 只读查询（读）→ 返回
```

- 只有"该同步了"的那一次请求执行写；其余纯读 → 并发安全 + 毫秒级响应
- 新表/新列要写快照字段（如 total_quantity/total_days/end_date），只读查询才不用回查主表

## 配套坑

- **新表权限**：用 postgres 超级用户建的表，应用用户（如 gaofang_app）无权限 → 500 `InsufficientPrivilege`。修复：
  ```sql
  GRANT ALL PRIVILEGES ON TABLE new_table TO app_user;
  GRANT ALL PRIVILEGES ON SEQUENCE new_table_id_seq TO app_user;  -- 别忘了序列！
  ```
- **验证"状态不被覆盖"**：标记一条状态 → 手动触发同步（走同一 UPSERT 路径）→ 查库确认状态仍在。这是 UPSERT 修复的回归测试核心。
- **并发测试方法**：单请求全过 ≠ 安全；必须并发压测（20 个并行 curl）才能暴露竞态。

## 参考

- 完整案例（膏方系统复诊模块 2026-08-03）：见 `gaofang-data-analysis` 技能的 `references/followup-module.md`（诊断路径、三层修复、并发测试脚本、性能数据）
