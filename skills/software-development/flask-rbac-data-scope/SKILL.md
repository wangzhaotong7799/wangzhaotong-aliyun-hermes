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
else:  # 药局：数量仍不可改
    data = {k: v for k, v in data.items() if k != 'quantity'}
```
前端编辑弹窗字段 `disabled` 同步，数量框置灰（#e9ecef 背景 + #6c757d 文字）。先问清业务规则再定编辑权限，别默认放大。
10. **⚠️ 下拉数据源不要只查业务表**：医助/用户下拉若只从 prescription_records 表 DISTINCT 查，**新建用户名下无历史处方 → 下拉永远为空**（"下拉没连上"）。改为：users 表（按业务角色 assistant/group_leader/director 过滤 + status=active + 按 get_visible_scope 过滤）**合并**业务表历史值（含离职/外部医助），去重排序返回。SQLAlchemy 老版本用 `.join(User.roles).filter(Role.id.in_(ids)).distinct()`（`exists().where()` 有兼容坑）。
11. **⚠️ 删除/改名角色必须同步前端**：数据库删角色（如删旧 admin/yaoju/pharmacy 角色）后，前端 `roles.indexOf('admin')` 等旧判断不会自动失效 → **被删角色的用户打不开对应页面**（实测 admin 打不开角色管理页）。删除前 `grep -rn "roles.indexOf\|roles.includes\|'admin'\|'yaoju'\|'pharmacy'\|'药局'" static/js/ static/mobile/js/` 全量排查，统一改为新角色名或 `checkPermission()` 权限点；后端 app.py/各 api 的 `set(['admin','yaoju',...])` 硬编码角色集合同样清理。
12. **时间范围过滤业务模式**："只显示本月+下月上半月窗口"：`fu1_planned_start >= 本月1日 AND fu3_planned_end <= 下月15日`（`_window_cutoff` 跨 12 月要处理 `year+1`）。PC 与移动端共用接口则同时生效；统计/排行接口保留全量。

## 实施顺序

1. 数据库迁移：新表 + users.group_id + 角色/权限点初始化 + 用户改名/新建（先 pg_dump 备份）
2. 后端：模型 + get_visible_scope + 各接口过滤（先全量加 @auth_required！）
3. 小组/总监范围管理接口（CRUD + 成员挂组 + scope 配置）
4. 前端：按 permissions 动态显隐（导航/列/按钮/编辑字段）
5. 测试 + 清 __pycache__ + HUP 重启 gunicorn

## 回归测试清单

- 匿名 GET/POST/DELETE → 401
- 各角色 get_visible_scope：超管/药局/领导层=None；总监=配置组；组长=本组；医助=自己
- can_view_field('prescription_type'/'doctor')：仅 admin/pharmacy_admin=True
- 领导层写接口 → 403
- GET /api/groups 权限：管理角色可、非管理角色 403
- 前端登录后 localStorage permissions 从 /api/auth/me 拉取

## 相关

- 基础 JWT RBAC（角色/权限表/装饰器）见 `flask-webapp-security-hardening`（注意：该技能为 hub 安装，curator 不可改，本技能补充其未覆盖的组织架构数据范围层）
