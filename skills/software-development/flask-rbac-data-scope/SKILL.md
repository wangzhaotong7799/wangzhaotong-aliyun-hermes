---
name: flask-rbac-data-scope
description: "Flask RBAC 组织架构数据范围 — 角色×小组双层权限模型、get_visible_scope 行级过滤、字段级权限、领导层只读、前端角色门控审计"
version: 1.0.0
author: Hermes Agent
tags: [flask, rbac, permission, data-scope, org-hierarchy, row-level, access-control]
toolsets_required: ['terminal', 'file']
category: software-development
metadata:
  hermes:
    tags: [flask, rbac, data-scope, row-level-security]
  applicability: flask-apps-with-org-hierarchy
  priority: high
---

# 🏢 Flask RBAC + 组织架构数据范围（get_visible_scope 模式）

## 适用场景

用户按角色分层（超管→药局管理员→领导层/总监/组长/医助），且**数据可见性由所属小组/门店决定**（总监看配置的小组、组长看本组、医助看自己）。要求全动态、不硬编码账号。

## 核心模型

角色决定功能权限（permissions 表），小组范围决定行级数据可见性。典型角色矩阵：

| 角色 | 数据范围 | 说明 |
|------|---------|------|
| super_admin | 全部 | 唯一可管药局管理员 |
| pharmacy_admin | 全部 | 可分配权限；字段级权限持有者 |
| leadership | 全部（只读） | 写接口一律 403 |
| director | director_group_scope 配置的小组 | 动态可配 |
| group_leader | 本组 | 店长/文员，看全店 |
| assistant | 自己 | |

## 表结构（增量）

- `groups(id, name, description)` — 小组表
- `director_group_scope(user_id, group_id)` — 总监可见小组范围（全量覆盖更新）
- `users.group_id` — 用户所属小组
- permissions 新增 `xxx:view` 权限点（如 prescription_type:view / doctor:view）控制字段级可见

## 数据范围解析（核心函数）

```python
def get_visible_scope(user_id=None):
    # super_admin/pharmacy_admin/leadership → None（全部可见）
    # director → director_group_scope 表的组 → 组成员 full_name+username 列表
    # group_leader → 本组成员列表
    # assistant → [自己的 full_name or username]
```

- 返回 `None` = 全部可见
- 返回 `[]` = 空（无可见数据）
- 返回列表 = 可见医助姓名集合，处方/复诊表按 `assistant IN (scope)` 过滤（含空值/'-' 兜底）

所有业务接口统一调用，**纯数据库查询，禁止硬编码账号**（移除旧 `SPECIAL_ACCOUNTS = ['yizhu001', ...]` 之类）。

## 关键实现要点（踩过的坑）

1. **所有业务路由必须加 `@auth_required`** —— get_visible_scope 依赖 g.user_id。把"手动解析 token"重构为统一函数时，漏加装饰器 = 数据范围失效 + **匿名可写漏洞**。回归测试必须含：匿名 GET/POST/DELETE → 401。
   **⚠️ 审计所有兄弟 Blueprint**：重构时逐个 grep 全部业务模块（prescriptions/followups/follow_up_management/stats/excel），看是否残留旧硬编码（`yizhu001|GJD|SPECIAL_ACCOUNTS`）或旧手动 token 解析（`verify_token(request.headers)`）——本次 followups.py（服用提醒）就漏改，仍用旧的 `_get_assistant_info` 白名单 + 无 @auth_required。
2. **字段级权限双保险**：后端无权限时置 None（`_mask_sensitive_fields`），前端按 `/me` 返回的 permissions 隐藏列/禁用输入框。
3. **领导层只读**：POST/PUT/DELETE/import/导出接口统一 403 拦截，前端隐藏按钮仅作 UX 同步。
4. **前端角色门控全量审计**：新增任何角色后，检查所有 `roles.indexOf(...)` 分支——导航显示、列显隐、按钮显隐、编辑弹窗字段禁用。漏掉则"登录后首页没有某菜单"（总监 director/组长 group_leader 曾被漏掉导航）。
5. **搜索过滤在可见范围内叠加**：`if assistant: query.filter(...)`，**不要**写成 `if assistant and get_visible_scope() is None:`——那会让总监/组长等非全量用户搜索失效。
6. **前端所有 fetch 必须带 token**：接口加 @auth_required 后，裸 fetch 全部 401（表现为下拉框为空）。统一用 fetchWithAuth 封装。
7. **批量建用户**：bcrypt 哈希 + 角色 + group_id 一次脚本建完。店长/文员用 group_leader 角色（看全店可改数据），医助用 assistant（看自己）。常见约定：用户名=姓名全拼，密码=用户名+123456。
8. **⚠️ 多角色用户误判（本次踩坑）**：用户可同时持多个角色（如 zj001 = assistant + director）。后端 `if 'assistant' in roles` 会把总监当纯医助限制（只能改 assistant+phone），前端同样误拦截"您没有编辑权限"。正确写法是算**"纯医助"**：`is_pure_assistant = 'assistant' in roles and not (director/group_leader/doctor/admin)`；前端同理用聚合布尔（`canEditBusiness = admin||doctor||yaoju||director||group_leader`）而非裸判单个角色。给用户加新角色后，必须复查所有 `'xxx' in roles` 判断点（编辑字段限制、操作列显隐、导航显隐、编辑弹窗门控）——总监/组长曾被漏掉导航和编辑按钮。
9. **⚠️ 编辑权限分层（主人纠正：最小权限）**：不要默认给 group_leader/director"可改业务数据"。实战规则：**仅 pharmacy_admin/super_admin 可编辑业务字段（医助/电话/发货时间/状态/是否传方）；其他角色（含 group_leader/director/assistant）只能改 医助+患者电话；`quantity` 数量字段全员只读（前端 disabled 置灰 + 后端白名单排除）**。后端实现：
```python
if not is_admin:  # 非药局
    allowed = ['assistant', 'patient_phone']
    data = {k: v for k, v in data.items() if k in allowed}
else:  # 药局：数量/剂型/医生仍不可改
    data = {k: v for k, v in data.items() if k not in ('quantity', 'prescription_type', 'doctor')}
```
前端编辑弹窗字段 `disabled` 同步，数量框置灰（#e9ecef 背景 + #6c757d 文字）。先问清业务规则再定编辑权限，别默认放大。
   **⚠️ 剂型/医生 = 永久只读（主人 2026-08 明确纠正）**：剂型和医生是**任何用户（含 pharmacy_admin/super_admin）都不能编辑**的字段——`prescription_type:view`/`doctor:view` 权限点只控制**可见性**（列显隐），**不控制编辑**。曾误把"查看权限"当"编辑权限"（`disabled = !canViewType`）导致药局拿到查看权限后也能编辑，主人纠正方向。正确实现：前端编辑弹窗中剂型/医生**永远 disabled**（所有角色）；后端 PUT 白名单把 `prescription_type`/`doctor` 与 `quantity` 一起排除（防绕过前端直接调 API）。修改字段编辑权限前，先确认业务规则（哪些字段本就该只读），不要看到"有人不能编辑"就当成 bug 修。
   **⚠️ 字段只读必须前后端双保险**：前端 disabled 只是 UX，恶意请求 PUT 仍可改 → 后端必须同字段过滤。验证：用超管 token PUT 尝试改该字段，确认数据不变。
10. **⚠️ 下拉数据源不要只查业务表**：医助/用户下拉若只从 prescription_records 表 DISTINCT 查，**新建用户名下无历史处方 → 下拉永远为空**（"下拉没连上"）。改为：users 表（按业务角色 assistant/group_leader/director 过滤 + status=active + 按 get_visible_scope 过滤）**合并**业务表历史值（含离职/外部医助），去重排序返回。SQLAlchemy 老版本用 `.join(User.roles).filter(Role.id.in_(ids)).distinct()`（`exists().where()` 有兼容坑）。
11. **⚠️ 删除/改名角色必须同步前端**：数据库删角色（如删旧 admin/yaoju/pharmacy 角色）后，前端 `roles.indexOf('admin')` 等旧判断不会自动失效 → **被删角色的用户打不开对应页面**（实测 admin 打不开角色管理页）。删除前 `grep -rn "roles.indexOf\|roles.includes\|'admin'\|'yaoju'\|'pharmacy'\|'药局'" static/js/ static/mobile/js/` 全量排查，统一改为新角色名或 `checkPermission()` 权限点；后端 app.py/各 api 的 `set(['admin','yaoju',...])` 硬编码角色集合同样清理。
12. **时间范围过滤业务模式**："只显示本月+下月上半月窗口"：`fu1_planned_start >= 本月1日 AND fu3_planned_end <= 下月15日`（`_window_cutoff` 跨 12 月要处理 `year+1`）。PC 与移动端共用接口则同时生效；统计/排行接口保留全量。
13. **⚠️ 登录后 permissions 竞态（前端字段权限全失效的隐蔽根因）**：登录成功代码里 `fetch('/api/auth/me')` 异步拉权限写入 localStorage，但**紧接着 `window.location.reload()` 立即执行** → 页面刷新打断 fetch，permissions 永远写入失败（null/空数组）→ `checkPermission('prescription_type:view')` 等全部返回 false → 前端按权限点控制的字段全部 disabled/隐藏（表现为"任何用户都不能编辑剂型/医生"——误以为权限配置错，实际是 permissions 没加载）。修复：把 reload 放进权限拉取的 Promise 链之后，并加超时兜底：
```javascript
var permissionFetch = fetch('/api/auth/me', {headers: {'Authorization': 'Bearer ' + data.token}})
    .then(r => r.json())
    .then(me => {
        var perms = (me && me.permissions) ? me.permissions.map(p => p.name || p) : [];
        localStorage.setItem('permissions', JSON.stringify(perms));
    })
    .catch(() => localStorage.setItem('permissions', '[]'));
var permissionTimeout = new Promise(resolve => setTimeout(resolve, 3000));
Promise.all([permissionFetch, permissionTimeout]).then(() => { window.location.reload(); });
```
**诊断顺序**：用户报"某字段所有人不能编辑/不可见" → ① 浏览器 console 查 `localStorage.permissions` 是否为 null/空（登录后）；② curl `/api/auth/me` 确认后端确实返回权限点；③ 若前端 null 而后端有 → 竞态 bug，不是权限配置问题。修复后**必须升 index.html 里 script 引用的 `?v=` 版本号**（Nginx `/static/` 缓存 7d immutable，不升版本号浏览器永远跑旧 JS——曾导致"修好了但页面还报错"）。

14. **⚠️ 医生角色：数据范围匹配不同列（doctor 而非 assistant）+ 业务归属规则**：新增 `doctor` 角色（医生只看自己的患者）时，数据范围返回的姓名列表要匹配 `model.doctor` 字段而不是默认的 `model.assistant`。实现：
```python
# auth.py — get_visible_scope() 加分支（放在"全部可见"之后）
if 'doctor' in role_names:
    return [user.full_name or user.username]  # 医生只匹配自己

# auth.py — 辅助函数（所有接口共享）
def is_doctor_role(user_id=None):
    from flask import g
    roles = getattr(g, 'roles', None)
    if roles is None:
        token = request.headers.get('Authorization')
        payload = verify_token(token[7:]) if token and token.startswith('Bearer ') else None
        roles = payload.get('roles', []) if payload else []
    return 'doctor' in roles

# 各接口过滤函数（prescriptions/followups/follow_up_management/stats 共 5 处同名函数）
if is_doctor_role():
    return query.filter(model.doctor.in_(scope))  # 医生按 doctor 列
# 其他角色继续走原有 model.assistant.in_(scope) 逻辑
```
   **⚠️ 医生可见性 = 只看自己名下的处方**（`doctor == 自己的 full_name`），**不包含"该医生名下医助的患者"**——主人明确业务规则：**医院存在一个医助跟 4-5 个医生的事实，归属以处方号对应的医生为准**（`prescription_records.doctor` 字段），不要动态推导医助归属（会把患者分给多个医生）。若需求提到"含医助患者"，先向主人确认归属规则再实现。
   **医生角色只读**：角色权限仅分配 `data:read`（无 `data:write`），仿 leadership 只读；前端操作列 `!roles.includes('doctor')` 才显示编辑按钮，隐藏导入/打印，保留查看/服用提醒/复诊/统计/导出（导出数据范围后端已过滤）。注意 `common.js` 的 `canSeeFollowup` 已含 `hasDoctor`（提醒/复诊菜单自动可见），只需确保编辑入口被门控。
   **⚠️ 复诊双确认例外（2026-08-13，主人拍板）**：医生对 `update_follow_up_status` **不再 403**——复诊改为「医助+医生双确认」，每次复诊（fu1/2/3）需医助+医生都确认才算成功；医生可确认范围 = **自己 + `doctor_user_doctors` 映射表医生名下**（如丛东海可确认崔玉华/张翠华名下；映射表同时驱动可见性过滤和写校验）。`stop_follow_up` 医生仍 403（停服不纳入双确认）。⚠️ JWT payload 无 full_name，医生归属校验须按 username 查 users 表 + 映射表合并成 `allowed_doctors` 集合。给角色放开写权限前先确认业务规则，别默认"只读角色一律 403"。完整状态机/迁移/验证配方见 `references/followup-dual-confirm.md`。
   **⚠️ 只读角色必须拦截 ALL 后端写接口（不只 PUT）**：曾实测医生 PUT 改医助返回 200（被"非药局角色只能改 assistant+phone"分支放行，未走 leadership 拦截）——只读角色要逐接口 grep 补拦截，拦截点统一写 `is_leadership or is_doctor`：
   - `prescriptions.py`: `update_prescription` (PUT) + `delete_prescription` (DELETE) — 两处 `_get_token_user_info()` 后判 `'leadership' in roles or 'doctor' in roles`
   - `followups.py`: `update_reminder_status` (POST) — 在 `_is_leadership_role()` 处加 `or is_doctor_role()`
   - `follow_up_management.py`: `update_follow_up_status` + `stop_follow_up`（两处 POST，各有一个手写 `verify_token` 判 leadership 的块，都要加 doctor）——**⚠️ 2026-08-13 例外：`update_follow_up_status` 医生已放开（双确认，限自己名下患者），`stop_follow_up` 仍 403**，见 `references/followup-dual-confirm.md`
   - `import` 接口有角色白名单（super_admin/pharmacy_admin/director/group_leader/assistant），doctor 不在白名单自动 403，无需改
   - 验证必须用**写接口实测**（登录医生账号 PUT/DELETE → 断言 403），不能只测 GET。
   **验证方法（批量账号过滤断言）**：逐个医生账号登录后 GET `/api/prescriptions?page=1&page_size=5`，断言 `total == SELECT count(*) FROM prescription_records WHERE doctor = full_name`（数据库直查对照），并断言返回记录的 `prescription_type` 非 null（剂型可见）。
   **新建医生用户**：`users.full_name` 必须与处方表 `doctor` 字段值**完全一致**（如"张翠华"），否则过滤结果为空。批量建用户脚本参考第 7 条（bcrypt + 角色 + 初始密码约定）。
   **⚠️ 多医生映射表（一个医生账号可看多位医生）**：医院存在"一位医生看多名医生名下患者"的需求（如丛东海要看崔玉华+张翠华的患者）。不要动态推导（医助归属会串），建显式映射表：
```sql
CREATE TABLE doctor_user_doctors (id SERIAL PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id),
  doctor_name VARCHAR(50) NOT NULL, UNIQUE(user_id, doctor_name));
```
   - 模型 `DoctorUserDoctor` 放 `models/doctor_user_doctor.py`，并在 `models/__init__.py` 注册导出
   - `get_visible_scope()` 的 doctor 分支改为：`names = [自己的 full_name]` + 查映射表 append 额外医生名（去重）
   - **⚠️ 新表权限陷阱（实测 500）**：用 postgres 超级用户建表后，应用连接用户（如 `gaofang_app`）**没有权限** → 接口 500 `permission denied for table doctor_user_doctors`（app.log 才看得到，gunicorn-error.log 不一定有）。必须执行：
     `GRANT ALL ON TABLE doctor_user_doctors TO gaofang_app;` + `GRANT USAGE ON SEQUENCE doctor_user_doctors_id_seq TO gaofang_app;`
     新建任何表后先确认应用 DB 用户权限，别等 500 才发现。
   **⚠️ 医生默认只显示最近 N 天，查询时看全部**（数据太多分页慢）：doctor 角色且**无任何查询/筛选参数**时默认加时间窗过滤，一旦带参数（patient_name/start_date/status/doctor/assistant 任一）就查全部历史：
```python
if not _is_guest and is_doctor_role() and not (
    start_date or end_date or status or patient_name or prescription_id or doctor or assistant
):
    cutoff = (date.today() - timedelta(days=90)).isoformat()
    query = query.filter(PrescriptionRecord.date >= cutoff)
```
   - 验证：默认列表 `total` 应 ≈ 数据库近 90 天 count；带 `start_date=2024-01-01` 后 total 应 = 全部历史 count。
   **医生可看剂型 = 给 doctor 角色分配 `prescription_type:view` 权限点**（只加 view，不加 `doctor:view`——医生列不需要显示其他医生名，数据全是自己的；不加 `data:write`——保持只读）。剂型列显隐和 `_mask_sensitive_fields` 后端隐藏都读这个权限点，只配前端不配后端 = 列显示了但值为 null。
   **⚠️ doctor:view（谁能看到处方的"医生"列）— 权限点分配实测（2026-08-12）**：`doctor:view` 只控制医生列**可见性**（无权限时后端 `_mask_sensitive_fields` 把 `doctor` 置 null，前端渲染 `(record.doctor || '')` 显示空；"按医生统计"整块隐藏），不控制编辑（医生字段所有角色永久只读）。当前分配：**super_admin / pharmacy_admin / leadership**（领导层需要看医生归属——主人明确指示，2026-08-12 加）；director / group_leader / assistant / **doctor 自己**均无。前端医生列无额外角色判断，随后端返回值自动显示。
   **⚠️ 改 role_permissions 即时生效，无需重新登录**：`check_permission`（含 `can_view_field`）每次请求**实时查库**（User→roles→permissions joinedload），不读 token 缓存。所以后端加权限点后，接口返回值（如 doctor 字段、统计块）立即变化；token 里的 roles 只用于前端菜单/按钮门控（存在 localStorage，改角色后需重新登录才反映）。"按权限点控制的后端返回值"与"前端角色门控"是两套机制，生效时机不同。

15. **⚠️ 显示被默认过滤排除的记录（"停服可见性"模式，2026-08-13 踩坑）**：需求"列表加停服时间列"时，停服患者默认被**三层过滤**挡掉，只改前端列=空列：
   - **死参数陷阱**：`include_stopped` 从 `request.args` 读出来了，但下面查询写死 `filter(is_stopped == False)`，参数从未生效。凡读出来的筛选参数必须实际拼进查询，否则是死参数。
   - **三层过滤必须联动松开**：① SQL 查询层 `filter(is_stopped == False)`；② 内存挑选层（`_pick_active_record` 里 `if rec.is_stopped: continue` 会把停服患者全部跳过、返回 None）；③ 时间窗口层（停服患者历史窗口早已过期，会被"本月+下月上半月"过滤排除）。改法：SQL 用 `or_(is_stopped == True, and_(is_stopped == False, 窗口条件))`；挑选函数加 `allow_stopped` 参数、全部停服时按 `month` 取 max 返回最新一条；窗口过滤对停服记录放行（在服记录保持原窗口规则）。
   - **新增字段历史回填**：加 `stopped_at` 后，历史 `is_stopped=True` 记录回填 `end_date + 40天`（自动停服理论日）；手动停服写当天。
   - **⚠️ 第 4 层过滤：日期范围过滤也会灭掉停服患者**：三层之外，列表接口还有"日期范围过滤"（按 fu 计划窗口交集判断），前端默认日期范围=今天~今天+3天 → 停服患者窗口全是过去日期 → 全灭（"勾了包含停服还是 0 人/列没数据"）。修复：`if patient.get('is_stopped'): filtered.append(patient); continue`。诊断法：同一请求带/不带 start_date&end_date 对比 total（本次 331→1671 定位）。
   - **在服患者也要显示停服时间（口径=领取+料数×30，主人最终纠正）**：`to_dict` 输出 `stop_time`——**停服时间 = end_date（领取时间+料数×30，药吃完那天）**，已停服患者同样显示 end_date。⚠️ 曾误用 end_date+40（系统自动停服跟踪规则）被主人纠正（"停服时间不是=料数×30天吗？"）；40 天只用于「停药时间 = 停服时间 + 40天」。前端「停服时间」列统一渲染 `patient.stop_time`——只用 stopped_at 则所有在服患者全是空。
   - **前端加列必须同步 colCount**：PC 表格加一列后，JS 里所有硬编码 `? 12 : 10`（空态 colspan 用）要同步改 `13 : 11`，共 5 处（用 replace_all），漏改导致"请先登录/加载中"占不满整行。三轮累计加列（停服时间→领取时间→电话）后最终为 `15 : 13`。
   - 完整实施记录 + 无需密码的接口验证脚本见 `references/followup-stopped-display.md`。

16. **⚠️ 新增独立页面（PC）菜单门控全量清单（5 处）+ 页面本体 6 步（2026-08-13 在服/停药患者明细页）**：新增任何带权限的页面，common.js 必须同步改 5 处，漏一处则"登录后看不到新菜单"或"未登录也能点"：① 导航元素获取（`getElementById('xxx-nav')`）；② 管理员分支 `canManage` 的 showNav 列表；③ 领导层分支 `hasLeader` 的 showNav 列表；④ 业务角色分支（如 `canSeeFollowup`）的 showNav/hideNav；⑤ 未登录分支的 hideNav 列表。页面本体：`templates/<page-name>.html`（**文件名必须与 pageName 完全一致**，连字符风格——`/page/<page_name>` 路由 `send_from_directory` 直接映射，无 Jinja 渲染）+ `static/js/page-<page-name>.js` 注册 `window.pageLoaders['<page-name>']`（common.js 自动 `?v=Date.now()` 注入，改 JS 无需升版本号）+ index.html 加导航 `<li id="xxx-nav">` 与容器 `<div id="page-xxx">`。⚠️ index.html 本体被 Nginx 缓存 7d，改导航必须提醒主人 Ctrl+F5 强刷。
   **剂型/医生列权限点分离**：新页面列显隐与后端掩码必须分两个权限点——剂型列=`prescription_type:view`、医生列=`doctor:view`；colCount 按两个权限点分别 +1（`9 + (canSeeSensitive?1:0) + (canSeeDoctor?1:0)`）。复诊管理页曾把两列共用一个 `prescription_type:view`，导致医生列权限与剂型列绑定。
   **明细页数据模式**：按患者去重取最近疗程（`max(recs, key=lambda r: r.end_date or date.min)`）；新增 `stop_time`（=end_date）、`drug_stop_time`（=end_date+40）；排序在服按 stop_time 升序、停药按 drug_stop_time 降序。\n   **医生下拉（\"所有医生\"搜索）**：专用接口 `/api/follow-up/doctors`——`_apply_scope_filter` 后对 `doctor` 列 DISTINCT 返回（医生角色自然只剩自己，医助/组长按各自可见范围）。不要从分页记录里提取（只含当前页医生，下拉不完整）；与医助 `/api/assistants` 一样要 `@auth_required`。
   **follow_up_records 加字段 4 处同步**（加 patient_phone 验证过）：① ALTER TABLE + 回填（从 prescription_records 用 `DISTINCT ON (patient_name,gender,age) ... ORDER BY id DESC` 取最新电话；postgres 超级用户执行，备份先行）；② `models/follow_up_record.py` 加 Column + `to_dict()`；③ `_sync_records` UPSERT：INSERT 列、VALUES、`DO UPDATE SET`、params 字典 4 处；④ `_group_patients` 分组 dict 带 `latest.get(...)`。漏 ③④ 则新数据不写新字段。
   - 完整新增页面配方（页面机制/导出列顺序/无密码验证/colCount 陷阱）见 `references/add-pc-page.md`。

17. **⚠️ 空字符串手机号唯一性误报（用户管理）**：`User.phone == ''` 会匹配库中所有空串手机号用户 → 编辑某个空手机号用户（前端提交 `phone:''`）时误报「手机号已被其他用户使用」，而库里查无重复。修复：`phone_val = (data['phone'] or '').strip()`，空值**跳过占用检查**并**存 NULL 而非 ''**；`register_user` 同样规范化 `(phone or '').strip() or None` 防新脏数据。历史脏数据清理：`UPDATE users SET phone = NULL WHERE phone = '';`。诊断路径：报占用但 `GROUP BY phone HAVING count(*)>1` 为空 → 查 `phone = ''` 的空串用户（psql 中 NULL 与 '' 显示都是空白，用 `phone IS NULL` / `phone = ''` 区分）。

## 实施顺序

1. 数据库迁移：新表 + users.group_id + 角色/权限点初始化 + 用户改名/新建（先 pg_dump 备份）
2. 后端：模型 + get_visible_scope + 各接口过滤（先全量加 @auth_required！）
3. 小组/总监范围管理接口（CRUD + 成员挂组 + scope 配置）
4. 前端：按 permissions 动态显隐（导航/列/按钮/编辑字段）
5. 测试 + 清 __pycache__ + HUP 重启 gunicorn

## 回归测试清单

- 匿名 GET/POST/DELETE → 401
- 各角色 get_visible_scope：超管/药局/领导层=None；总监=配置组；组长=本组；医助=自己
- can_view_field('prescription_type')：admin/pharmacy_admin/doctor=True（医生可看剂型）
- can_view_field('doctor')：admin/pharmacy_admin/leadership=True，其余（含 doctor 自己）False
- 领导层写接口 → 403
- GET /api/groups 权限：管理角色可、非管理角色 403
- 前端登录后 localStorage permissions 从 /api/auth/me 拉取

## 相关

- 基础 JWT RBAC（角色/权限表/装饰器）见 `flask-webapp-security-hardening`（注意：该技能为 hub 安装，curator 不可改，本技能补充其未覆盖的组织架构数据范围层）
