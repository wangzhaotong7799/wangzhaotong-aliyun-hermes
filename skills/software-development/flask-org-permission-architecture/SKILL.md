---
name: flask-org-permission-architecture
description: "Flask 组织架构权限体系设计 — 角色×小组×数据范围×字段级权限，含角色生命周期（新增/删除）审计清单、多角色优先级、PostgreSQL 迁移实操"
version: 1.0.0
author: Hermes Agent
tags: [flask, rbac, permissions, organization, groups, data-scope, field-level, sqlalchemy]
toolsets_required: ['terminal', 'file']
category: software-development
metadata:
  hermes:
    tags: [flask, rbac, permissions, organization, groups, data-scope]
  applicability: flask-apps-with-org-hierarchy
  priority: high
---

# 🏛️ Flask 组织架构权限体系（角色 × 小组 × 数据范围）

## 适用场景

当权限需求超出「管理员/普通用户」两级，出现**组织层级**时：

- 医助只看自己名下、组长看本组、总监看配置的小组、领导层看全部但只读
- 多门店/多分支/多团队，每人归属一个小组，上级按小组范围看数据
- 敏感字段（剂型、医生、价格）只有特定角色可见
- 用户、小组、总监范围都要求**界面动态配置，不写死在代码里**

> 关联技能：`flask-webapp-security-hardening` 覆盖 JWT/RBAC 后端基础；本技能覆盖组织层级扩展。两者配合使用。

## 核心设计：五层模型

1. **角色**（roles 表，动态）— 决定"能做什么"：super_admin / pharmacy_admin / leadership / director / group_leader / assistant
2. **小组**（groups 表，动态）— 组织归属：`users.group_id` 外键
3. **总监范围**（director_group_scope 表，动态）— director 可见哪些小组（多对多）
4. **数据范围**（运行时解析）— 决定"能看到哪些行"
5. **字段级权限**（`xxx:view` 权限点）— 决定"能看到哪些列"

## 权限矩阵示例（膏方系统真实落地）

| 角色 | 数据范围 | 敏感字段(剂型/医生) | 写操作 |
|------|---------|-------------------|--------|
| super_admin | 全部 | ✅ | 全部 |
| pharmacy_admin | 全部 | ✅ | 全部 + 分配权限 |
| leadership | 全部 | ❌ | 纯只读（列表+详情） |
| director | 配置的小组 | ❌ | 业务写，不能改剂型 |
| group_leader | 本组所有成员 | ❌ | 业务写，不能改剂型 |
| assistant | 自己名下 | ❌ | 纯医助只能改医助+电话 |

## 数据范围解析（核心函数）

```python
def get_visible_scope(user_id=None):
    """None = 全部可见；[str,...] = 可见医助姓名列表"""
    role_names = {r.name for r in user.roles}
    if role_names & {'super_admin', 'pharmacy_admin', 'leadership'}:
        return None  # 全部
    if 'director' in role_names:
        group_ids = [s.group_id for s in DirectorGroupScope.filter_by(user_id=uid)]
        return _collect_names(User.filter(group_id.in_(group_ids)))  # 查表，无硬编码
    if 'group_leader' in role_names:
        return _collect_names(User.filter(group_id == user.group_id))
    return [user.full_name or user.username]  # assistant：自己
```

- 优先级：super_admin > pharmacy_admin > leadership > director > group_leader > assistant
- `_collect_names` 同时收集 full_name 和 username（处方表 assistant 字段两种都可能存）
- 所有业务查询统一 `query = _apply_scope_filter(query, Model)`，禁止各模块自己写过滤逻辑

## 角色生命周期（新增/删除）——必须全量审计

### 新增角色时
`grep -n "roles.includes\|roles.indexOf\|hasRole\|in roles"` **逐文件**审计：
- 前端操作列/编辑按钮显隐（`actionHeader.style.display`）
- 前端导航菜单显隐（common.js updateLoginStatus）
- 编辑弹窗字段禁用逻辑
- 后端 `'x' in roles` 判断（app.py、各 blueprint）

漏一处 = 该角色登录后看不到编辑按钮/菜单（本技能作者真实踩坑：店长/文员/总监看不到膏方记录编辑按钮，且 openEditModal 被"您没有编辑权限"拦截）。

### 多角色用户优先权（pure-assistant 模式）
用户可同时有 assistant+director（总监兼医助）。**后端和前端都必须用「纯医助」判断**：

```python
is_business_editor = 'director' in roles or 'group_leader' in roles or 'doctor' in roles
is_pure_assistant = 'assistant' in roles and not is_business_editor and not is_admin
if is_pure_assistant:  # 才限制只能改 assistant+patient_phone
```

否则 `is_assistant` 会把总监误限为医助权限。

### 删除角色时（审计清单）
1. 备份数据库
2. 查角色使用情况确认兜底：
   `SELECT r.name, COUNT(DISTINCT ur.user_id) FROM roles r LEFT JOIN user_roles ur ... GROUP BY r.id`
3. 确认每个在用用户的**兜底角色**（如 admin 用户同时有 super_admin）
4. `DELETE FROM user_roles WHERE role_id=...; DELETE FROM role_permissions WHERE role_id=...; DELETE FROM roles WHERE name=...`
5. **grep 全部代码中的旧角色名**——尤其前端 `roles.indexOf('admin') === -1` 守卫，角色删了会导致管理员打不开管理页（真实踩坑）
6. 登录验证兜底角色权限完好

## ⚠️ 硬编码账号白名单散落多文件

`SPECIAL_ACCOUNTS = ['yizhu001', 'GJD-A', 'GJD-B']` 这类硬编码往往在**多个 blueprint 同时存在**（prescriptions.py、follow_up_management.py、followups.py...）。统一化时：

```bash
grep -rn "SPECIAL_ACCOUNTS\|yizhu001\|GJD-A" --include="*.py" api/ auth.py app.py
```

全量替换为 `get_visible_scope()`，漏一个模块就残留旧权限。

## PostgreSQL 迁移实操（踩坑记录）

- `su - postgres -c "psql -d <db> -f <file.sql>"` 要求 SQL 文件对 postgres 可读——项目目录下常 Permission denied，先 `cp` 到 `/tmp` + `chown postgres:postgres`
- 新建表必须授权应用用户：`GRANT SELECT,INSERT,UPDATE,DELETE ON <table> TO <app_user>; GRANT USAGE ON SEQUENCE <seq> TO <app_user>;` 否则 InsufficientPrivilege
- 模型带 `created_at` 而表没有 → 先 `ALTER TABLE ... ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT now()`
- 权限逻辑改动后必须：清 `__pycache__` + 发 `kill -HUP <gunicorn_master_pid>`（HUP 平滑重载 workers）

## 前端部署提醒

Nginx 静态缓存 7 天，改完 JS 必须提醒用户 **Ctrl+F5 强刷**，否则新界面不生效。移动端 PWA 改 JS 要同步递增 `?v=` 版本号和 `CACHE_NAME`。

## 参考文件

- `references/gaofang-v2-rollout.md` — 膏方系统真实落地记录（表结构 SQL、迁移顺序、验证清单）
