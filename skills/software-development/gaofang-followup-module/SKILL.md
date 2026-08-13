---
name: gaofang-followup-module
description: "复诊管理模块开发 — 表结构、双确认机制、业务口径、停服过滤陷阱、界面/导出加列链路"
version: 1.0.0
author: Hermes Agent
tags: [flask, gaofang, follow-up, 复诊, 膏方, xlsx-export]
toolsets_required: ['terminal', 'file']
category: software-development
metadata:
  hermes:
    tags: [flask, gaofang, follow-up, 复诊]
  applicability: gaofang-v2-followup-development
  priority: high
---

# 膏方系统复诊管理模块开发

## 适用场景

主人要求修改膏方管理系统 V2 的复诊管理（`/api/follow-up*` + `templates/followup.html` + `static/js/page-followup.js`）：加列、改导出、调停服逻辑、加电话等。代码路径 `/workspace/projects/drug-distribution-system/gaofang-v2/`，服务 `gaofang-v2-fusion`（gunicorn 0.0.0.0:8080，venv38）。

## 业务口径（主人明确纠正过，禁止再错）

- **停服时间 = 领取时间 + 料数×30天**（即 `end_date = pickup_date + total_quantity*30`）。**不是** end_date+40！
- **停药时间 = 停服时间 + 40天**（明细页「停药时间」列 = `end_date + 40`，与系统自动停服清理规则同口径）。
- `end_date + 40天` 只是**系统自动停服清理规则**（`is_stopped=True`、`stopped_at=end_date+40`），用于从跟踪列表移除，不是业务上"停服时间"。界面「停服时间」列统一显示 `end_date`（`to_dict` 的 `stop_time` 字段）。
- 手动停服接口（`/follow-up/stop`）写 `is_stopped=True` + `stopped_at=当天`（实际停服日），保留在 `stopped_at` 字段，界面列不显示它。
- 复诊时段 = 取药后 10~19 / 20~29 / 30~39 天循环到服用结束；距取药 <5 天整体顺延 10 天；截止 = 服用结束日+10天（续方观察期）。
- 复诊列表默认只显示「本月+下月上半月」窗口内的在服患者；统计/排行接口保留全量。

## follow_up_records 表关键字段（2026-08 现状）

`patient_name/gender/age/patient_phone/assistant/prescription_id/prescription_type/doctor/pickup_date/total_quantity/total_days/end_date/month/fu1|fu2|fu3_(status,date,planned_start,planned_end,assistant_date,doctor_date)/is_stopped/stopped_at/created_at/updated_at`
- 唯一键 `(patient_name, gender, age, month)`，UPSERT 按此冲突更新。
- `patient_phone` 和 `stopped_at` 是 2026-08-13 新增（历史上没有），已回填。
- `fuX_assistant_date` / `fuX_doctor_date`（2026-08-13 新增，双确认机制）：医助/医生各自确认日期。

## 复诊双确认机制（2026-08-13 上线）

每次复诊（fu1/2/3）需**医助 + 医生都确认**才算「已复诊」：

- **数据**：`fuX_assistant_date`（医助确认日）+ `fuX_doctor_date`（医生确认日）。两者齐 → `fuX_status='已复诊'`、`fuX_date=max(a,d)`（第二个确认日）；否则 `fuX_status='待复诊'`、`fuX_date=None`。
- **模型** `to_dict` 用 `_fu_status(num)` 重算状态（读日期字段而非 status 列）；`follow_up_X_status`/`follow_up_X_assistant_date`/`follow_up_X_doctor_date` 都输出；`follow_up_status` 总状态也按 `_fu_status` 重算。update 接口同时维护 status 列（统计接口 SQL 用列值）。
- **接口** `POST /api/follow-up/update`（body: record_id, follow_up_number, status）：
  - 后端按角色强制 `confirm_role`：**医生角色 → doctor 确认；其他业务角色（医助/药局）→ assistant 确认**。前端不用传 confirm_role。
  - **医生放开只读**（原来 403）：只能确认**自己 + doctor_user_doctors 映射表**名下的患者（如丛东海→崔玉华/张翠华、于明霞→蒋汶轩；`get_visible_scope` 的 doctor 分支同表）。校验：`record.doctor not in allowed_doctors → 403`。
  - 领导层仍 403 只读；`status` 只接受 已复诊/待复诊（待复诊=撤回自己的确认，对方确认保留）。
- **历史迁移**：旧已复诊记录（无确认字段）→ `fuX_assistant_date=fuX_doctor_date=fuX_date`（双确认视为完成，不补确认人）。
- **前端 PC**：fuCell 显示「医助✓ 医生✓」双状态点（都绿=已复诊）；编辑弹窗改为双确认模式（每行显示对方✓+我的✓+我的确认/撤回按钮，按角色只显示自己的按钮，领导层显示只读）。
- **前端 PWA**：`fuStatusBadge` 双状态点 + `fuActionButton` 按 `Store.hasRole('doctor')` 显示「医生确认N/医助确认N」按钮；`Store.isLeadership()` 不渲染按钮。
- 统计/排行口径不变（`fuX_status == '已复诊'` 由 update 接口维护正确）。

## ⚠️ 停服患者"查得到但列表不显示"的三层过滤陷阱

用户报"停服时间列没数据/停服患者看不到"时，按序排查（曾全部踩中）：

1. **SQL 层无条件过滤**：`get_follow_up_patients` 曾写死 `.filter(is_stopped == False)`，`include_stopped` 参数读了但没用。修复：`if not include_stopped and follow_up_status != '已停服'` 才过滤。
2. **窗口过滤**：`fu3_planned_end >= 本月1日 AND fu1_planned_start <= 下月15日` 会排除历史停服患者。修复：`show_stopped` 时改为 `or_(is_stopped==True, and_(is_stopped==False, 窗口条件))`——停服记录不限窗口。
3. **`_pick_active_record` 跳过停服记录**：患者所有时段 is_stopped 时返回 None 被丢弃。修复：加 `allow_stopped` 参数，全停服时返回最新一条。
4. **前端默认日期范围**（页面加载器设置 今天~今天+3天）：后端日期范围过滤按复诊窗口交集判断，停服患者窗口全是过去日期 → 被过滤。修复：日期范围过滤时 `if patient.get('is_stopped'): continue`（停服患者跳过）。

验证自洽性：默认 total + 停服患者数(按患者去重) == include_stopped total；筛选"已停服" total == 停服患者数。

## 加新列/新字段的完整链路（漏一步就出 bug）

1. **数据库**：`ALTER TABLE follow_up_records ADD COLUMN xxx ...`（先 `pg_dump` 备份到 `backups/`）；历史回填（如电话：从 `prescription_records` 按 patient_name+gender+age 匹配最新记录）。
2. **模型** `models/follow_up_record.py`：加 Column + `to_dict()` 输出（字段名带 `isoformat()`）。
3. **同步 UPSERT** `_sync_records`（api/v1/follow_up_management.py）：INSERT 列、VALUES 参数、ON CONFLICT DO UPDATE 三处 + `params` 字典 + `_group_patients` 返回值——**漏加则下次全量同步把新字段清空/丢新数据**。
4. **模板** `templates/followup.html`：表头 `<th>`。
5. **JS 渲染** `static/js/page-followup.js`：渲染行 `<td>` + **colCount 硬编码 5 处同步 +1**（`? 15 : 13` 之类，按角色敏感列差异）。
6. **导出** `exportFollowUpData()`：加列 + 顺序重排（见下）。

## 在服/停药患者明细页面（2026-08-13 新增，独立页面）

两个独立 PC 页面：**在服患者明细**（`active-patients`）、**停药患者明细**（`stopped-patients`）。列：患者姓名→性别→年龄→电话→处方类型*→数量→医生*→医助→领取时间→停服时间→停药时间（* 权限列）。

**后端接口**（follow_up_management.py）：
- `GET /api/follow-up/patients?type=active|stopped&patient_name=&assistant=&doctor=&page=&page_size=` — 按患者去重取**最近疗程**（`max(recs, key=lambda r: (r.end_date or date.min, r.month or date.min))`）；`stop_time=end_date`、`drug_stop_time=end_date+40`；排序：在服按 stop_time 升序（先停药优先）、停药按 drug_stop_time 降序（最近停药优先）；返回分页 `{data,total,...}`。
- **在服口径必须与统计概览一致**：`type=active` 过滤 `is_stopped=False AND end_date >= date.today()`。曾因明细页只过滤 `is_stopped=False` 导致 415 vs 统计概览 322 不一致（多出的是「药已吃完、还没到 40 天自动停服」的 98 人）。主人报「统计概览和卡片数量不一致」时先查这个。
- 必须 `_mask_sensitive_fields(d)`：无权限时 `prescription_type`/`doctor` 置 None（`can_view_field`，与 followup 页面只用单个 flag 不同，明细页医生列用 `doctor:view` 权限点）。
- `GET /api/follow-up/doctors` — 医生下拉数据源：可见范围内 `DISTINCT doctor` 排序返回。**别学 prescriptions 页从当前页记录提取**（只含当前页 50 条，下拉不全）。

**PC 新页面接线标准流程**（common.js 懒加载机制）：
1. `templates/<name>.html` — `/page/<page_name>` 路由自动 `send_from_directory('templates', f'{page_name}.html')`，文件名必须与 pageName 完全一致（连字符）。
2. `static/js/page-<name>.js` — common.js 自动注入脚本并调 `window.pageLoaders['<name>']()`；JS 里注册 `window.pageLoaders['<name>'] = init`。ID 前缀防冲突（ap-/sp-）。
3. `static/index.html`：导航 `<li id="<name>-nav" style="display:none;">` + 页面容器 `<div id="page-<name>" class="page-content">`。
4. `static/js/common.js` 权限门控（4 个分支都要加）：canManage 分支、hasLeader 分支、canSeeFollowup 分支、未登录 hideNav 分支。漏一处 = 部分角色看不到菜单。
5. 分页控件/表格/加载器模板仿 `page-followup.js`；页面上方合计数量用统计卡（`card text-center shadow-sm d-inline-block` + `border-left` 彩色边，数字随筛选 total 实时更新）。
6. 导出用 `XLSX.utils.aoa_to_sheet([headers].concat(rows))` 严格控列序（比 json_to_sheet 更直白，权限列中间插入无需重排对象）。

## 导出规则（主人 2026-08-13 明确要求）

- **导出列顺序 = 界面列顺序**（含权限列位置：处方类型在数量前、医生在医助前；无权限时跳过）。
- **复诊时间列 = 已复诊 → 实际日期 `fuX_date`；待复诊 → 计划窗口 `fuX_start~fuX_end`**（主人强调"待复诊的时间很重要"，只导 `fuX_date` 会漏掉所有待复诊患者的时间）。
- 实现：`row` 对象键插入顺序即 Excel 列序（`json_to_sheet` 按键序）；权限列动态插入时用 `orderedHeaders` 数组重排再 `json_to_sheet`。

## 界面列结构（2026-08-13 快照，加列后需同步更新此处）

操作 | 患者姓名 | 性别 | 年龄 | 电话 | 处方类型* | 数量 | 医生* | 医助 | 回访状态 | 领取时间 | 停服时间 | 复诊1 | 复诊2 | 复诊3
（\* = prescription_type:view 权限可见；colCount 有权限 15 / 无权限 13）

## PWA（移动端）加新页面接线（2026-08-13 在服/停药明细）

PWA 在 `static/mobile/`，与 PC 完全独立：

1. `static/mobile/index.html`：底部导航 `<a href="#/name" data-tab="name" class="nav-guest-hidden">`（游客隐藏）+ `<script src="/mobile/js/page-name.js?v=N">` 引入（版本号 +1）。
2. `static/mobile/js/page-name.js`：`Router.register('name', render)` 注册路由；render() 内先 `Router.updateNav('name')` 高亮；页面模块 IIFE 包裹。
3. `static/mobile/js/api.js`：加对应 `Api.getXxx(params)` 方法（qs 构建与 getFollowups 同款）。
4. 底部导航是 `display:flex; flex:1` 自适应，加 tab 不用改 CSS；**5 个 tab 是上限**（领取/复诊/在服/停药/提醒），再增需合并入口。
5. 卡片式渲染 + 本地搜索过滤（全量 `page_size:5000` 拉取）+ 「加载更多」按钮（STEP 50）——大列表（1300+ 条）不卡顿。
6. **Nginx 7d immutable 缓存坑**：`/mobile/` 在 `/static/` 下，index.html 被强缓存，新 tab 和新 JS 会"看不到"。sw.js 是 network-first（JS/CSS 网络优先，自动更新），但 **index.html 必须强刷/清站点数据**才能拉到新版。改完 PWA 必提醒主人强刷。

## 膏方系统其他模块坑（2026-08-13 实测）

### 编辑用户改姓名报「手机号已占用」（误报）
- 根因：`auth.py update_user` 里 `if data['phone'] and not validate_phone(...)` 只校验非空，但占用检查 `User.phone == data['phone']` **不判空** → 前端 phone 留空提交 `''` 时匹配到库里 `phone=''` 的历史脏数据（如 yizhu010）→ 误报。
- 修复：空 phone 跳过占用检查 + 存 NULL（`user.phone = phone_val if phone_val else None`）；`register_user` 同步规范 `(phone or '').strip() or None`；清理历史 `UPDATE users SET phone=NULL WHERE phone=''`。
- 排查顺序：查 yizhu016.phone（NULL）→ 查全库 `phone=''` 用户 → 定位误匹配源。

### 编辑处方改医助 → 同患者同日记录联动更新（主人要求）
- 需求：编辑 `PUT /api/prescriptions/<id>` 修改 assistant 时，**同「日期+姓名+性别+年龄+手机号」的记录一起改**（同一患者同一天多料记录保持医助一致）。
- 实现：for 循环 setattr 后、commit 前，`session.query(PrescriptionRecord).filter(id != 当前, date==, patient_name==, gender==, age==)` + 手机号匹配（非空精确；空值用 `or_(phone.is_(None), phone=='')` 否则 NULL≠'' 漏配）→ `.update({'assistant': new}, synchronize_session=False)`，记 logger 留痕。
- 匹配键用 `data.get('date', record.date)`（新值优先，改其他字段时按新键联动）。

## 统计数字差异排查（角色数据范围，通常不是 bug）

主人报「两个账号统计的在服患者不一样」（如 yaoju002=323 vs zj001=321）时：

1. **先查角色**：`pharmacy_admin/super_admin/leadership` → 全量（scope=None）；`director` → 管辖小组（`director_group_scope`）的 active 成员 full_name+username；`assistant` → 只看自己；`group_leader` → 本组。
2. **关键：`_apply_scope_filter` 对医助为空的记录（`assistant IS NULL / '' / '-'`）全部可见**——所以总监看到的远多于「可见医助名下」的数（321 不是 260）。
3. **总监范围不含自己**：`get_visible_scope` 总监分支收集小组成员（`_collect_names` 含 full_name + username），如果总监自己 `group_id=None`（不属于任何组），**自己名下的患者对自己不可见**。案例：曹莹莹（zj001）是总监+医助，她的账号 group_id=None，自己名下的 2 个在服患者（董金凤、牛玉芬）在她界面消失 → 321 vs 323 差 2。修复方向：总监范围 append 自己的 full_name + username（医生分支同款做法）。
4. 排查方法：实测各账号 `GET /api/follow-up/statistics` + `patients?type=active` 的真实返回（不要自己模拟 scope，`get_visible_scope` 依赖请求上下文 g.user_id，独立脚本模拟容易算错），再用接口返回的患者键集合做差集定位。

## 验证方法（无密码也可测）

```python
# 项目 venv38，直接用 generate_token 绕过登录（auth.py 有 generate_token(user_id, username, roles)）
from app import app; from database import db; from auth import generate_token; from models import User
with app.app_context():
    u = db.session.query(User).filter_by(username='yaoju001').first()
    token = generate_token(u.id, u.username, [r.name for r in u.roles])
    client = app.test_client()
    r = client.get('/api/follow-up?include_stopped=1&page=1&page_size=5', headers={'Authorization': f'Bearer {token}'})
```
- 写接口验证用**临时测试记录**（INSERT 假患者 → 调接口 → SELECT 断言 → DELETE），测完即删不污染数据。
- 测试 INSERT `prescription_records` 必须给 `prescription_id` 和 `doctor`（都有 NOT NULL 约束，缺一报 NotNullViolation；`follow_up_records` 无此约束）。
- 重启：`kill -HUP $(systemctl show gaofang-v2-fusion -p MainPID --value)`（HUP 热重启，不中断请求）；`find . -name __pycache__ -type d -exec rm -rf {} +` 清理缓存。
- 前端 JS 动态加载带 `?v=Date.now()` 无需升版本号；**改完提醒主人 Ctrl+F5 强刷**（Nginx /static/ 缓存 7d immutable）。

## 相关技能

- 权限/数据范围（get_visible_scope、医生只读、字段级权限）→ `flask-rbac-data-scope`
- 数据库统计口径 → `gaofang-data-analysis`
