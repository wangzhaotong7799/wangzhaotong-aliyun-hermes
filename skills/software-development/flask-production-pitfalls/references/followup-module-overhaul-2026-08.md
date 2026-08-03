# 膏方管理系统复诊模块改版（2026-08）完整案例

Flask + PostgreSQL + Gunicorn(4w×4t) 生产环境。业务：中医膏方患者复诊管理。

## 业务规则（用户确认的最终版）

1. **复诊患者** = status='已取' 的患者，按 姓名+性别+年龄 去重，一个患者显示一条
2. **服用期** = 最近取药前 7 天内料数累加 × 30 天（与服用提醒逻辑一致）
3. **复诊时段** = 取药后 10~19 / 20~29 / 30~39 天，下月 +30 天循环，直到服用结束（截止 = 结束日 + 10 天缓冲，覆盖续方观察期）
4. **太近顺延** = 距取药 < 5 天 → 所有时段整体顺延 10 天（复诊1 从 +20~29 开始）
5. **停服** = 手动标记 is_stopped 或 服用结束超 40 天自动停服
6. **权限** = yizhu001/GJD-A/GJD-B 看全部，普通医助只看自己名下
7. 历史已复诊数据不迁移（用户选 A），统计从改版月起算

## 数据结构

新表 `follow_up_records`（每患者每月一行，3 个复诊位）：
```
id, patient_name, gender, age, assistant, prescription_id, prescription_type, doctor,
pickup_date, total_quantity, total_days, end_date,   ← 服用期快照（PC 表格显示用）
month（该月第一个复诊窗口日期，定月份锚点）,
fu1/2/3_status, fu1/2/3_date, fu1/2/3_planned_start/end,
is_stopped, created_at, updated_at,
UNIQUE (patient_name, gender, age, month)   ← 约束名 uq_followup_patient_month
```
⚠️ 新表用 postgres 建后要给应用用户授权：
```sql
GRANT ALL PRIVILEGES ON TABLE follow_up_records TO gaofang_app;
GRANT ALL PRIVILEGES ON SEQUENCE follow_up_records_id_seq TO gaofang_app;
```

## 并发修复链（踩坑顺序）

1. 最初 `_sync_records` 用 ORM「查询→没有→add→commit」→ 4 worker 并发撞唯一键 → 500 HTML → PWA 报 `Unexpected token '<'`
2. 改原生 SQL UPSERT（text + ON CONFLICT DO UPDATE，只更新计划字段保留状态字段）→ 并发不再报错，但仍慢
3. 性能：每患者一次 commit（1596 患者）→ 146 秒；改单事务批量提交（commit=False 循环 + 末尾一次 commit）→ 3.7 秒；GET 接口主体改只读查询 → 0.06 秒
4. 节流：5 分钟时间戳文件 + fcntl.flock(LOCK_EX|LOCK_NB) 跨进程互斥，GET 只有第一个请求触发全量同步，其余只读
5. `_pick_active_record` fallback bug：全部时段过期也返回最早记录 → 修复为「进行中优先 → 未来时段预告 → 过期不显示」

## 统计正确性（Pattern 5 实际案例）

- ❌ 旧：GET 传 `follow_up_status=follow_up_1_pending`（后端筛掉已复诊）→ 前端统计已复诊恒为 0
- ✅ 新：GET 不带筛选（limit=5000，全量 326 人/246KB）→ 前端 filterByTab 过滤列表 + renderStats 基于全量统计「待复诊 X / 已复诊 Y / 共 Z」
- 王静标记复诊1已复诊后：复诊1 tab = 待 325 / 已 1 / 共 326 ✓
- 合计 tab 的「已复诊」= 3 次全部完成（用户明确：只来 1 次、2 次不算）

## 缓存修复链

1. Nginx `/static/` 配 `expires 7d; Cache-Control "public, immutable"` → 浏览器 7 天不重新请求 JS
2. 症状迷惑：字段名没变的列（prescription_type/doctor）能显示，变了的列（quantity→total_quantity）空 → 旧 JS 读旧字段名
3. 修复：common.js 动态加载加 `?v=' + Date.now()`；index.html 引用 common.js 加 `?v=20260803`；SW CACHE_NAME v2→v3 + JS/CSS network-first；mobile/index.html JS 引用 v2→v3→v4→v5 递增
4. 用户侧：Ctrl+F5 强刷

## 前端 ID 不匹配（Pattern 4 实际案例）

- page-admin-users.js 写 `edit-username/edit-full-name/edit-email/edit-phone`，HTML 实际 `edit-user-username/edit-user-fullname/edit-user-email/edit-user-phone`
- 创建表单同样问题（create-username vs create-user-username 等 5 处）
- 现象：点编辑报「获取用户信息失败」，接口日志 200 正常
- 修复：正则对比脚本找出全部不匹配 → 统一修正；顺带把编辑时角色区域改为只读徽章显示（原代码找错元素，角色区域空白）

## 验证方法

- 并发压测：`for i in $(seq 1 20); do (curl ... ) & done; wait`，全 200 JSON 才算过
- Flask test client 批量检查 Content-Type（排除 HTML 响应）
- 用 generate_token(user_id, username, roles) 生成测试 JWT（注意 user_id 必须是数据库真实用户 id，否则权限判定错乱——测试 yizhu001 用 id=27 而非 1）
