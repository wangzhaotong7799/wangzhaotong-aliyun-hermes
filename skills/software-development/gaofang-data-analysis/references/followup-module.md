# 复诊/回访模块（follow-up）—— 实施后基线（2026-08-03）

> 改造**已完成并上线**（2026-08-03 会话实施）。旧逻辑备份在 `backups/followup_logic_backup_20260803_095633/`（backend/ pc/ mobile/ 共12文件，md5 校验一致）。项目是 git 仓库（master）。
> 改动文件：`models/follow_up_record.py`（新）、`api/v1/follow_up_management.py`（重写）、`api/v1/stats.py`、`database.py`、`models/__init__.py`、`static/mobile/js/page-followup.js`、`static/mobile/css/app.css`、`static/js/page-followup.js`、`templates/followup.html`。

## 新表 follow_up_records（方案B：每患者每月一行，3 复诊位）

| 字段 | 说明 |
|------|------|
| patient_name / gender / age / assistant | 患者快照（归组=姓名+性别+年龄，**不含手机号**） |
| prescription_id / prescription_type / doctor / pickup_date | 最近取药快照（处方类型/医生也是快照列，PC 表格靠它们显示） |
| total_quantity / total_days / end_date | 服用期快照（料数×30天；end_date 是停服状态灯的计算基准） |
| month (date, NOT NULL) | 该月首个复诊窗口日期（定月份锚点） |
| fu1/2/3_status (默认'待复诊') | 各次复诊状态 |
| fu1/2/3_date | 实际复诊日期（标'已复诊'自动记当天；改回'待复诊'清空） |
| fu1/2/3_planned_start/end | 计划窗口（展示用） |
| is_stopped (bool) | 停服标记（end_date+40 自动标 True） |
| 唯一键 | UNIQUE (patient_name, gender, age, month) |

模型：`models/follow_up_record.py`，**必须在 `models/__init__.py` 和 `database.py` 的 `init_db()`（逐模块 import 列表）两处注册**，否则 create_all 不会建表。

## 复诊时段生成规则（最终版）

- 服用期 = 最近取药前 **7 天**内料数累加 × 30 天（与 reminders 口径一致）
- 时段：`pickup+10~19 / +20~29 / +30~39`，下月 `+40~49 / +50~59 / +60~69`…每 30 天一轮
- 截止：**服用结束日 + 10 天缓冲**（`end_date = pickup + total_days + 10`）——没有这个缓冲，1 料（30天）患者顺延后第 3 次复诊（+40）超出截止会被整段丢弃 → 时段数=0 的边界 bug
- 太近顺延：`(today - pickup).days < 5` → base_offsets 从 `[10,20,30]` 改为 `[20,30,40]`（整体顺延 10 天）
- 自动停服：`(today - end_date).days >= 40` → is_stopped=True（与 reminders 的 40 天逻辑并行）
- 状态持久化在表，计划窗口每次 GET 动态同步（pickup 变化自适应）

## API 变更

| 接口 | 变化 |
|------|------|
| GET /api/follow-up | 返回 FollowUpRecord.to_dict() + total_quantity/total_days/end_date + **pinyin/pinyin_initial**（搜索用）；每患者一条（当前应进行的时段，停服默认过滤，`include_stopped=1` 可带出） |
| POST /api/follow-up/update | **参数改为 `record_id` + follow_up_number(1-3) + status**；兼容旧 `patient_id`+`month` 定位 |
| POST /api/follow-up/stop | 新接口：按 patient_name+gender+age 标记该患者全部时段 is_stopped=True（前端已不手动调用，停服/已停药改为自动状态灯） |
| GET /api/follow-up/statistics | 按 month 分组统计（排除停服），权限：special 看全部 / 医助看自己 |
| GET /api/follow-up/ranking | 同上权限 |

## 权限模型细节（测试时踩过坑）

- special 账号：yizhu001/GJD-A/GJD-B（`_get_assistant_info` 按 payload['user_id'] 查库判断 username）
- 列表过滤（普通医助）：`assistant == 自己 OR null/''/'-'` —— **包含 '-'**，所以 '-' 占位的患者医助也看得到
- 统计/排行过滤（普通医助）：`FollowUpRecord.assistant == 自己` **精确匹配，不含 '-'**
- ⚠️ **测试 token 必须用真实 user_id**：`generate_token(user_id, username, roles)` 里 `_get_assistant_info` 用 `payload['user_id']` 查库，传 admin 的 id=1 冒充 yizhu001 会被判定为普通医助（'系统管理员'）→ 统计返回空、列表却正常（因为列表过滤含 '-'）。真实 id：yizhu001=27（曹莹莹）、admin=1。验证权限用 `su - postgres -c "psql -d gaofang_v2 -c 'SELECT id, username, full_name FROM users'"`。

## 实施陷阱（2026-08-03 遇到并解决）

1. **PostgreSQL 新表权限**：用 postgres 超级用户建的表，`gaofang_app` 无权限 → 500 `InsufficientPrivilege`。修复：
   ```sql
   GRANT ALL PRIVILEGES ON TABLE follow_up_records TO gaofang_app;
   GRANT ALL PRIVILEGES ON SEQUENCE follow_up_records_id_seq TO gaofang_app;
   ```
   （owner 仍显示 postgres，但授权后 gaofang_app 可读写）
2. **PC 端保存 bug 已修**（原：前端传 `id`，后端读 `patient_id` → 400 静默失败）：前端改传 `record_id`，且 `.then` 遇 `data.error` 必须 `throw` 中断，避免"看起来成功实际没存"。
3. **JS 中文引号陷阱**：PWA 字符串拼接 `'...' + num + '」...'` 里混入中文右引号 `」` 当字符串边界 → SyntaxError。拼接字符串只用 ASCII 引号。
4. **Gunicorn 热重启**：`kill -HUP <master_pid>`（master 是启动最早、`Ss` 状态的进程），workers PID 会换新。项目用 `--reuse-port`。

## 遗留（主人待定）

历史已复诊数据**未迁移**：旧表 prescription_records 的 follow_up_1/2/3_status='已复诊' 记录仍在旧字段，新表从'待复诊'开始 → 统计复诊率从 0 起算。选项 A 不迁移 / B 按日期归入新表对应时段。reminders（服用提醒）仍用旧表 follow_up_status，与新表 is_stopped 并行。

## ⚠️ 上线后第二轮修复（并发崩溃 + 性能 146s→0.06s）—— 最重要的一课

**症状**：主人报「加载失败: Unexpected token '<', \"」。这是前端 `res.json()` 解析到 **HTML**（Flask 500 错误页）的经典签名——不是浏览器缓存问题！

**根因链（诊断路径）**：
1. 直接 curl 8080 各 API → 全部 200 JSON（因为单请求不触发竞态）
2. 并发压测（20 个 curl 同时打）→ 全部卡死/超时
3. gunicorn-error.log → `UniqueViolation: duplicate key value violates unique constraint "uq_followup_patient_month"` —— **Gunicorn 4 workers 并发执行「查询→没找到→INSERT」**，同一患者同一月同时插入撞唯一键 → 500 HTML
4. 深层问题：GET 列表接口每次请求都全量写库（1596 患者组 × 3600+ 条 UPSERT），并发必冲突

**修复（三层）**：
1. **写库改 PostgreSQL 原生 UPSERT**（SQLAlchemy 1.3 没有 `on_conflict_do_update`，必须用原生 SQL）：
   ```python
   from sqlalchemy import text
   upsert_sql = text("""
       INSERT INTO follow_up_records (patient_name, gender, age, assistant, ..., month, ...)
       VALUES (:patient_name, :gender, :age, ..., :month, ...)
       ON CONFLICT (patient_name, gender, age, month)
       DO UPDATE SET assistant = EXCLUDED.assistant, pickup_date = EXCLUDED.pickup_date,
           fu1_planned_start = EXCLUDED.fu1_planned_start, ... /* 只更新计划字段 */
   """)
   ```
   **关键**：`DO UPDATE SET` 只更新计划窗口/快照字段，**不碰 fu1/2/3_status、fu1/2/3_date、is_stopped** —— 已复诊状态和手动停服标记并发下也保留（已验证：标记已复诊 → 触发同步 → 状态仍在）。
2. **节流 + 跨进程文件锁**：`_maybe_sync(session)` 用 `/tmp/followup_sync_state`（5 分钟间隔）+ `/tmp/followup_sync.lock`（fcntl.flock LOCK_EX|LOCK_NB，非阻塞拿不到就跳过）—— 只允许一个 worker 做全量同步，其余请求纯只读。
3. **单事务批量提交**：`_sync_records(..., commit=False)` + `_sync_all_patients` 末尾一次 `session.commit()`。原来每患者 commit 一次（1596 次）→ **146 秒**；单事务一次提交 → **3.7 秒**；5 分钟窗口内只读查询 → **0.06 秒**。

**接口架构原则（本次教训）**：GET 列表接口**永远不要每次请求全量写库**。正确模式 = 「节流同步（写）+ 只读查询（读）」分离。同步函数里**不要在循环中查询 ORM 对象**（会触发 autoflush 把未提交的 UPSERT 全部 flush，更慢）。

**顺带修复**：
- `_pick_active_record` fallback bug：全部时段窗口已过期（fu3_end < today）的患者不应显示；修复后只返回「进行中时段」或「最早的未来时段（下月预告）」，全过期返回 None。**第五轮又调整**：全过期但未停服（<40天）的患者仍显示（为了停服/已停药状态灯可见），+40 天自动停服后移除。
- 服用期快照字段 `total_quantity / total_days / end_date` 加到了 follow_up_records（模型 + `ALTER TABLE ADD COLUMN IF NOT EXISTS` + UPSERT 写入），让只读查询无需回查 prescription_records。
- 新表用 postgres 建的要 `GRANT ALL ON TABLE ... TO gaofang_app` + `GRANT ALL ON SEQUENCE ... TO gaofang_app`（见上文陷阱1）。
- PWA 缓存：改前端后 `CACHE_NAME` 升到 v3，且 CSS 与 JS 一样走 network-first（原来 CSS 是 cache-first，改样式不生效）。

**并发测试方法**：写 bash 并发脚本（20 个 `curl &` 后台并行 + `wait`），逐个检查响应首字符是 `[`（JSON 数组）还是 `<`（HTML）。之前单请求测试全过、并发才暴露问题。

## 上线后第三轮修复：处方类型/医生快照 + Nginx 静态缓存（2026-08-03 同会话）

**问题1：PC 表格「处方类型/数量/医生」列空**。原因：follow_up_records 只存了患者基础信息，没存 prescription_type/doctor 快照；且「数量」列接口只返回 `total_quantity`（服用期总料数），前端旧字段 `quantity` 不存在。

**修复**：
- 模型加 `prescription_type`、`doctor` 列（快照，取最新一条已取记录的剂型/医生）
- `ALTER TABLE follow_up_records ADD COLUMN IF NOT EXISTS prescription_type VARCHAR(100), ADD COLUMN IF NOT EXISTS doctor VARCHAR(50)`
- `_group_patients` 从 latest 记录提取 `prescription_type`/`doctor`，UPSERT SQL 加这两列
- 改后 `rm -f /tmp/followup_sync_state` 强制触发一次全量同步补数据（约 3.9s），此后 5 分钟窗口内只读

**问题2：「数量」列仍空，但处方类型/医生已显示** → 排查发现是 **Nginx 静态缓存**：
```nginx
location /static/ {
    alias .../static/;
    expires 7d;
    add_header Cache-Control "public, immutable";
}
```
浏览器 7 天内不重新请求 JS。主人浏览器缓存了**旧版 page-followup.js**（数量列读 `patient.quantity`，新接口无此字段 → 空；处方类型/医生字段名没变 → 能显示，造成"只差数量"假象）。

**排查证据**：`curl -s -I http://127.0.0.1:8080/static/js/page-followup.js | grep -i cache` → `Cache-Control: no-cache`（Flask 直连）；但实际部署经 Nginx 80 端口，`nginx -T 2>/dev/null | grep -B3 -A8 "expires 7d"` 实锤。

**修复（cache-busting，不动 Nginx）**：
```html
<!-- index.html 静态引用加版本号 -->
<script src="/static/js/common.js?v=20260803"></script>
```
```javascript
// common.js 动态加载脚本加时间戳（否则动态 createElement 的 script 同样被缓存）
script.src = '/static/js/page-' + pageName + '.js?v=' + Date.now();
```
- PWA：`mobile/index.html` JS 引用 `?v=2`→`?v=3`，`sw.js` CACHE_NAME v2→v3，且 CSS 与 JS 一样 network-first
- 改完仍需用户 **Ctrl+F5 强刷一次**（当前页还引用旧 URL）

**教训**：Flask 直连 curl 验证的响应头（no-cache）≠ 实际部署链路（Nginx `expires 7d immutable`）。前端"部分字段空且后端全对"时，先 `nginx -T` 查静态缓存配置，用版本号 cache-busting，不要改 Nginx 缓存策略。

## 上线后第四轮：PWA 统计 Tab 改版 + 统计数字 bug（2026-08-03 同会话）

**需求**：PWA 复诊页顶部按钮从「待复诊/已完成」改为 4 个：**本月复诊1统计 / 本月复诊2统计 / 本月复诊3统计 / 本月复诊合计（默认 tab）**，按复诊次数筛查看待复诊患者。

**统计数字 bug（主人纠正）**：医助标记王静复诊1=已复诊后，「本月复诊1统计」仍显示已复诊 0 人。主人预期 **待复诊325 / 已复诊1 / 共326**。

**根因**：初版实现是后端按 tab 传 `follow_up_status=follow_up_N_pending` **筛选后再返回**，前端统计基于**筛选后的列表** —— 已复诊的患者已被后端过滤掉，前端根本看不到 → 已复诊恒为 0、总数也错（325 而非 326）。

**修复（模式：统计必须基于全量数据）**：
- 前端一次拉全量：`Api.getFollowups({ limit: 5000 })`（**不带 follow_up_status**；实测 326 人 ≈ 246KB，远小于旧接口 4MB 崩溃阈值）
- 显示列表 = 前端本地按 tab 过滤（`filterByTab`：fuN 看 `follow_up_N_status !== '已复诊'`；合计看任一未完成）
- 统计 = 基于**全量** listData 算 待/已/共，绝不基于过滤后的子集
- 默认 tab = `TABS[0]`（all）；改前端后 PWA 版本号 `?v=4→v5`（SW network-first 会自动拉新）

**通用教训**：任何「统计数字」必须来自全量数据集，不能来自已被筛选器过滤的子集 —— 被筛掉的数据（已复诊的）不会出现在统计里。主人会手工核对数字（"应该是待325已1共326"），统计口径必须与手工核对一致才算对。

## 上线后第五轮：admin 用户管理「获取用户信息失败」（2026-08-03 同会话）

**症状**：admin 用户管理界面点「编辑」→ alert「获取用户信息失败」。接口日志显示 GET /api/auth/users/30、/31 全部 200 正常。

**根因**：`static/js/page-admin-users.js` 的 `getElementById` ID 与 `templates/admin-users.html` 实际 ID **不匹配**：
```javascript
// JS 写的（错误）         HTML 实际的
edit-username      →    edit-user-username
edit-full-name     →    edit-user-fullname
edit-email         →    edit-user-email
edit-phone         →    edit-user-phone
```
`getElementById('edit-username')` 返回 null → `null.value = xxx` → TypeError → 被 `.catch` 吞掉 → 显示「获取用户信息失败」（实际错误是 `Cannot set properties of null`）。**创建用户表单同样 5 处不匹配**（create-username vs create-user-username 等）。接口 200 但前端 DOM 抛错 —— 后端完全无辜。

**快速验证脚本**（改前端表单后必跑）：
```python
import re
html = open('templates/admin-users.html').read()
js = open('static/js/page-admin-users.js').read()
html_ids = set(re.findall(r'id="([^"]+)"', html))
js_ids = set(re.findall(r"getElementById\('([^']+)'\)", js))
print([i for i in sorted(js_ids) if i not in html_ids])  # → [] 才是全部匹配
```
用 `node --check` 只能查语法，**查不出 ID 悬空** —— 必须做 ID 交叉核对。

**修复**：JS 全部改用 HTML 实际的 `edit-user-*` / `create-user-*` ID；保存 payload 去掉 `role_id`（update_user 不支持，角色走独立接口）；编辑时角色区显示为只读徽章（原代码找 `edit-user-role` select 但 HTML 是 `edit-user-roles-container` div）。

**通用教训**：前端报「XXX失败」且接口 200 时，先看 `.catch` 里吞掉的真实错误（console 或 alert 全文本），再核对 JS 引用的 DOM ID 是否存在于页面 HTML —— ID 不匹配是「保存/编辑无反应或报错但后端正常」的头号前端根因之一。

## 上线后第六轮：搜索首拼 + 停服/已停药自动状态灯（2026-08-03 同会话）

**需求1：搜索支持首拼查询**（输入 `wj` 找到王静、`lcf` 找到林长发）。
- 后端 GET /api/follow-up 组装 result 时用 `utils/pinyin.py`（pypinyin 库）给每条加：
  ```python
  from utils.pinyin import get_pinyin, get_pinyin_initial  # 全拼 wangjing / 首字母 wj
  d['pinyin'] = get_pinyin(pname)
  d['pinyin_initial'] = get_pinyin_initial(pname)
  ```
- 前端 `getVisibleList()` 过滤：`name.indexOf(kw) || pinyin.indexOf(kwLower) || pinyin_initial.indexOf(kwLower) || 性别/年龄/医助` —— 中文关键词用原串、拼音关键词用小写化后的串。
- 性能：326 条 × 2 次 pypinyin 调用，返回时算一次，<1ms，无压力。

**需求2：停服/已停药改为自动状态灯**（主人原话：不用用户编辑，按逻辑来 —— 到停服时间自动变绿；到停服+40天已停药变绿；其他时间灰色）。
- 前端 `renderCards` 按 `end_date` 计算（**必须本地解析日期字符串**，`new Date('YYYY-MM-DD')` 在 UTC+8 会偏移 8 小时导致当天判断错误）：
  ```javascript
  function parseLocalDate(s) { var p = s.split('-'); return new Date(+p[0], +p[1]-1, +p[2]); }
  stopLight:     isDatePast(end_date, 0)  ? 绿 '停服'   : 灰
  drugStopLight: isDatePast(end_date, 40) ? 绿 '已停药' : 灰
  ```
- 移除手动 stop/drugstop 按钮绑定和 handleStop 函数（后端 /follow-up/stop 接口保留但前端不再调用）。
- 配套后端调整 `_pick_active_record`：全部时段过期但 `is_stopped=False`（<40天）的患者**仍返回**（状态灯可见），+40 天自动停服后才从列表消失。
- PWA 版本号递增 `?v=6→v7`。

**通用教训**：
- 模糊搜索加拼音：后端补 pinyin/pinyin_initial 字段比前端引拼音库更干净（项目已有 pypinyin）。
- 前端日期比较用 `new Date(y, m-1, d)` 本地构造，不要用 `new Date('YYYY-MM-DD')` 字符串构造（时区偏移坑）。
- 「自动状态灯」类需求：去掉手动操作入口，前端按时间字段计算展示状态，后端自动逻辑（40 天停服）保持不变。
