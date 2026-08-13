# 复诊双确认改造（2026-08-13，膏方V2 follow_up_records）

## 背景
复诊状态原为单方确认（谁改都是已复诊）。改为：每次复诊（fu1/2/3）需**医助+医生双确认**，都齐才算成功；医生从纯只读放开为"仅可确认自己名下患者的复诊"。

## 数据模型（增量，已执行）
- `follow_up_records` 新增 6 列：`fu{1,2,3}_assistant_date`、`fu{1,2,3}_doctor_date`（DATE）
- 既有 `fuX_status`/`fuX_date` 保留：status 由后端在双确认齐时置 `'已复诊'`；`fuX_date = max(两个确认日)`
- 模型 `to_dict()` 加 `_fu_status(num)` **重算**：`a_date and d_date → '已复诊'`，否则 `'待复诊'`。前端/排行/导出都吃这个重算值，status 列即使没更新也能正确显示（历史兜底）
- 历史迁移：已复诊记录 → `assistant_date=doctor_date=fuX_date`（不补确认人）；备份先行

## 状态机（api/v1/follow_up_management.py → update_follow_up_status）
- 入参：`record_id` + `follow_up_number` + `status`（'已复诊'=确认 / '待复诊'=撤回）
- 后端按 token 角色**强制** `confirm_role`：`'doctor' in roles → doctor 确认`；其他业务角色 → assistant 确认（前端无需传）
- 医生校验（**含多医生映射表**）：可确认范围 = 自己 full_name + `doctor_user_doctors` 映射表医生名（如 丛东海→崔玉华/张翠华、于明霞→蒋汶轩），`record.doctor` 不在集合内 → 403「只能确认自己名下的患者」
- 领导层仍 403；`stop_follow_up` 医生仍 403（停服不纳入双确认）
- 每次更新后重算：`a and d → status='已复诊', fuX_date=max(a,d)`；否则 `status='待复诊', fuX_date=None`
- 撤回 = 清自己角色的日期（对方确认保留）

## ⚠️ JWT 陷阱
`generate_token` payload 只有 `user_id/username/roles`（**无 full_name**）。医生确认范围必须按 username 查 `users` 表拿 `full_name`，再查 `DoctorUserDoctor` 映射表（`user_id` → `doctor_name` 列表），合并成 `allowed_doctors` 集合后比对 `record.doctor`。

## 前端
- PC `page-followup.js`：`fuCell` 显示「医助✓/医生✓」双状态点（都绿=已复诊）；编辑弹窗改双确认模式（fuRow 每行：对方确认+我的确认+我的按钮），按角色 `isDoctor`/`isLeader` 渲染；渲染行编辑按钮 data 属性改为传 `data-fuN-a`/`data-fuN-d` 日期（不再传 status）
- PWA `page-followup.js`：`fuStatusBadge` 双状态；`fuActionButton` 按 `Store.hasRole('doctor')` 渲染「医生确认N」/「医助确认N」；`Store.isLeadership()` 只读不变

## 同模块踩坑（可复用）
1. **日期范围过滤会隐形滤掉历史记录**：列表接口默认 `start_date=今天,end_date=+3天`，停服患者窗口全是过去日期 → 全被滤掉，表现为"列没有数据"。修复：停服患者（is_stopped）跳过日期范围过滤。
2. **include_stopped 参数读了没用**：`get_follow_up_patients` 曾无条件 `filter(is_stopped==False)`，参数解析了从未应用。修复：show_stopped 时不过滤 + `_pick_active_record` 加 `allow_stopped` 返回停服记录 + 停服记录不受"本月+下月上半月"窗口限制（SQL `or_(is_stopped==True, and_(...)`）。
3. **统计口径必须对齐**：明细卡片(415) vs 统计概览(322) 不一致——明细少一个 `end_date >= today` 条件。新增列表/统计端点必须与既有端点过滤条件对齐并验证数字。
4. **停服/停药时间业务口径**：停服时间 = 领取时间 + 料数×30（=end_date），**不是** end_date+40（+40 是系统自动停服规则，用于「停药时间」）。停药时间 = 停服时间 + 40天。
5. **导出列顺序**：JS 对象键顺序 = Excel 列顺序；权限条件列（处方类型/医生）用 `orderedHeaders` 数组重建对象保证有/无权限时列序一致（先插权限列再插其余）。

## 页面添加模式（本 app PC 端）
新独立页面 = `templates/<name>.html`（路由 `/page/<page_name>` 自动映射）+ `static/js/page-<name>.js`（注册 `window.pageLoaders['<name>']`）+ `index.html` 加 nav `<li>`（`display:none`）+ `<div id="page-<name>" class="page-content">`。common.js 菜单显隐三处分支（canManage / hasLeader / canSeeFollowup）都要加新 nav，未登录分支 hideNav 也要加。表格 colspan 列数同步。

## 验证配方（临时记录法）
INSERT 测试记录 → 医助确认（assistant_date 写入，status 仍待复诊）→ 非本人医生确认 → 403 → 本人医生确认（双确认→已复诊，fuX_date=max）→ 医生撤回（回待复诊，医助保留）→ 领导层写 → 403 → DELETE 清理。断言用数据库直查对照。
