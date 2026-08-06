---
name: flask-organizational-rbac
description: "Flask 组织架构权限模型 — 角色×小组/门店数据范围双层权限（医助看自己/店长看本店/总监看多店/领导层只读），含数据库设计、get_visible_scope 统一解析、前端角色显隐清单、下拉数据源与角色删除陷阱"
version: 1.0.0
author: Hermes Agent
tags: [flask, rbac, authorization, data-scope, row-level-security, org-hierarchy, sqlalchemy]
toolsets_required: ['terminal', 'file']
category: software-development
metadata:
  hermes:
    tags: [flask, rbac, authorization, data-scope, row-level-security, org-hierarchy, sqlalchemy]
  applicability: production-flask-apps
  priority: high
---

# 🏢 Flask 组织架构权限模型（Org-Hierarchy RBAC）

## 🎯 适用场景

业务系统需要「角色 × 小组/门店/科室数据范围」双层权限时：

- 医助/组员只看自己名下数据
- 店长/组长看本组（本店）所有成员数据
- 总监看多个小组（范围可配置）
- 领导层看全部但纯只读
- 药局管理员可分配权限、唯一可见敏感字段（剂型/医生）
- 新增小组/用户/总监范围必须**界面配置、不写死代码**

## 🗄️ 数据模型（增量设计）

```sql
CREATE TABLE groups (                    -- 小组/门店/科室
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL,    -- 「一组」「康安路店」
    description VARCHAR(200),
    created_at TIMESTAMP DEFAULT now(),
    updated_at TIMESTAMP DEFAULT now()
);

CREATE TABLE director_group_scope (      -- 总监可见小组范围（多对多，界面配置）
    user_id INT NOT NULL REFERENCES users(id),
    group_id INT NOT NULL REFERENCES groups(id),
    PRIMARY KEY (user_id, group_id)
);

ALTER TABLE users ADD COLUMN group_id INT REFERENCES groups(id);
```

角色建议：`super_admin` / `pharmacy_admin`（可分配权限）/ `leadership`（只读）/ `director` / `group_leader` / `assistant`。
权限点建议：`user:*`、`role:manage`、`group:*`、`director_scope:manage`、`data:all/read/write/export/import`、敏感字段 `xxx:view`（如 `prescription_type:view`、`doctor:view`）。

## ⚙️ 核心：get_visible_scope() 统一数据范围解析

单一入口，所有业务接口复用。返回 None=全部可见，否则返回可见的医助姓名列表（**full_name + username 都收集**，业务表可能存任一种）。

```python
def get_visible_scope(user_id=None):
    """优先级：super_admin > pharmacy_admin > leadership > director > group_leader > assistant"""
    role_names = {r.name for r in user.roles}
    if role_names & {'super_admin', 'pharmacy_admin', 'leadership'}:
        return None  # 全部
    if 'director' in role_names:
        scope_rows = db.session.query(DirectorGroupScope).filter_by(user_id=user.id).all()
        group_ids = [s.group_id for s in scope_rows]
        if not group_ids:
            return []
        return _collect_names(db.session.query(User).filter(
            User.group_id.in_(group_ids), User.status == 'active').all())
    if 'group_leader' in role_names:
        if not user.group_id:
            return []
        return _collect_names(db.session.query(User).filter(
            User.group_id == user.group_id, User.status == 'active').all())
    return [user.full_name or user.username]  # assistant：自己
```

统一过滤器（每个接口先按范围过滤，再叠加业务条件）：

```python
def _apply_scope_filter(query, model):
    scope = get_visible_scope()
    if scope is None:
        return query
    from sqlalchemy import or_
    if not scope:
        return query.filter(or_(model.assistant.is_(None), model.assistant == '', model.assistant == '-'))
    return query.filter((model.assistant.in_(scope)) | (model.assistant.is_(None)) |
                        (model.assistant == '') | (model.assistant == '-'))
```

## 🔒 字段级权限（敏感字段双保险）

- 后端：`can_view_field('prescription_type')` 查 `xxx:view` 权限点，无权限返回时字段置 None（列表/详情/统计/导出全链路）
- 前端：登录后拉 `/api/auth/me` 的 permissions 存 localStorage，`checkPermission('xxx:view')` 控制列显隐与输入框禁用
- 统计接口：无权限时不返回医生/剂型分组

## ✏️ 编辑字段权限矩阵（常见业务规则）

| 字段 | 药局管理员/超管 | 其他角色 |
|------|:---:|:---:|
| 医助、患者电话 | ✅ | ✅ |
| 状态、发货时间、是否传方 | ✅ | ❌ 白名单过滤 |
| 剂型、数量、医生 | 按 `xxx:view` | ❌ |

后端：非 `super_admin`/`pharmacy_admin` 一律 `allowed_fields = ['assistant', 'patient_phone']`。
前端：所有登录用户都能打开编辑弹窗，字段按角色 disabled（优于入口拦截——提示友好且防误伤）。

## ⚠️ 陷阱清单（全部实测踩过）

1. **重构时装饰器丢失**：手动解析 token（`verify_token(request.headers)`）重构为依赖 `g.user_id` 的统一权限函数时，必须给**所有路由补 `@auth_required`**，否则数据过滤失效 + 匿名可写。用匿名请求测 GET/POST/DELETE 应 401 验证。
2. **前端角色菜单漏配**：新增角色后逐处检查——导航菜单、表格操作列、编辑弹窗 disabled、管理页入口。用聚合变量（`canSeeFollowup = hasDoctor || hasAssistant || hasDirector || hasGroupLeader`）避免每处手写漏一个。
3. **下拉/枚举数据源**：只从业务表查 DISTINCT 值 → 新用户（无历史数据）在下拉里永远看不到。合并 users 表在职用户（限定业务角色）+ 业务表历史值。旧版 SQLAlchemy `exists().where(a, b)` 报错，用 `query.join(User.roles).filter(Role.id.in_(ids)).distinct()` 替代。
4. **双角色误判**：用户可同时挂 `assistant`+`director`（原医助升总监）。判断"纯医助"必须排除业务编辑角色，否则总监被当普通医助限制。
5. **角色删除回扫**：删角色前 `grep -rn "'角色名'" static/ --include="*.js"` + 后端 `--include="*.py"`。前端写死 `roles.indexOf('admin') === -1` 会在角色删除后把管理员锁在页面外。
6. **新表权限**：建表后 `GRANT SELECT/INSERT/UPDATE/DELETE ON 新表 TO 应用用户; GRANT USAGE ON SEQUENCE 新表_id_seq TO 应用用户;`（PostgreSQL 应用用户非 owner 时必做）。
7. **双角色数据范围**：用户同时有 assistant+leadership（如领导层账号挂过 assistant）时，优先级判断必须先命中 leadership → 全部可见，不会被 assistant 分支限制。

## 🚀 部署/回归清单

1. 清 `__pycache__` → `kill -HUP <gunicorn master pid>` 平滑重载
2. 回归：各角色登录 → 数据范围条数差异；字段脱敏；匿名 401；写接口按角色 403/字段过滤
3. 前端静态文件有 Nginx 缓存时提醒用户 Ctrl+F5 强刷
4. 改动生产库前 `pg_dump` 备份

## 🔗 关联

- 基础 RBAC/JWT 集成见 `flask-webapp-security-hardening`（JWT 角色、guest login、前端路由守卫）
- 本技能是其「组织架构行级权限」扩展层

*创建时间*: 2026-08-06
*适用项目*: 膏方管理系统 V2 权限架构重设计（Flask + SQLAlchemy + PostgreSQL）
