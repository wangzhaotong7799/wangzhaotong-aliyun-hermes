---
name: flask-permission-empty-tables
description: 排查 Flask 应用中 `@permission_required` 装饰器始终返回 403 的问题 — Permission 表或 role_permissions 关联为空导致的权限不足
version: 1.0.0
tags: [flask, permission, rbac, 403, database-seeding]
---

# Flask `@permission_required` 总是 403？— 权限表空的排查与修复

## 症状

- admin 登录后调用 `@permission_required('user:read')` 的接口返回 403
- 所有用户（无论什么角色）都看到 `{"error": "权限不足"}`
- 控制台显示：`GET /api/auth/users 403 (FORBIDDEN)`

## 根因

`@permission_required` 是**数据库运行时检查**，不是静态角色名检查。它调用 `check_permission(g.user_id, permission_name)` 实时查数据库：

```python
def check_permission(user_id, permission_name):
    user = db.session.query(User).options(
        joinedload(User.roles).joinedload(Role.permissions)
    ).filter_by(id=user_id).first()
    for role in user.roles:
        for perm in role.permissions:
            if perm.name == permission_name:
                return True
    return False  # Permission 表为空时总是返回 False！
```

当以下情况发生时，所有权限检查都会失败：
1. `Permission` 表通过 `create_all()` 创建但**从未填充数据**
2. `role_permissions` 关联表存在但**没有关联记录**
3. 从 V1（无 RBAC）迁移到 V2（有 `@permission_required`）时遗漏了播种脚本

## 诊断方法

在 Python shell 中验证：

```python
from app import app
from database import db
from models import Role, Permission

with app.app_context():
    session = db.session
    
    # 检查 admin 角色的权限
    admin_role = session.query(Role).filter_by(name='admin').first()
    print(f"Admin permissions: {[p.name for p in admin_role.permissions]}")
    # 输出: []  ← 空的！
    
    # 检查数据库中有没有权限记录
    all_perms = session.query(Permission).all()
    print(f"Total permissions in DB: {len(all_perms)}")
    # 输出: 0  ← 根本没有权限记录！
```

## 修复方法

创建标准权限并分配给 admin 角色：

```python
from app import app
from database import db
from models import Role, Permission

with app.app_context():
    session = db.session
    
    # 1. 创建所需权限
    perms = [
        ('user:read', '查看用户'), ('user:create', '创建用户'),
        ('user:update', '更新用户'), ('user:delete', '删除用户'),
        ('role:read', '查看角色'), ('role:create', '创建角色'),
        ('role:update', '更新角色'), ('role:delete', '删除角色'),
    ]
    for name, desc in perms:
        if not session.query(Permission).filter_by(name=name).first():
            session.add(Permission(name=name, description=desc))
    session.flush()
    
    # 2. 所有权限分配给 admin
    admin_role = session.query(Role).filter_by(name='admin').first()
    if admin_role:
        for p in session.query(Permission).all():
            if p not in admin_role.permissions:
                admin_role.permissions.append(p)
        session.commit()
```

## 预防措施

在首次部署时运行播种脚本：

```python
def seed_permissions():
    with app.app_context():
        session = db.session
        if session.query(Permission).count() > 0:
            return  # 已播种
        
        perms = [Permission(name=n, description=d) for n, d in [
            ('user:read', '查看用户'), ('user:create', '创建用户'),
            ('user:update', '更新用户'), ('user:delete', '删除用户'),
            ('role:read', '查看角色'), ('role:create', '创建角色'),
            ('role:update', '更新角色'), ('role:delete', '删除角色'),
        ]]
        session.add_all(perms)
        session.flush()
        
        admin_role = session.query(Role).filter_by(name='admin').first()
        if admin_role:
            admin_role.permissions.extend(perms)
            session.commit()
```

在 `app.py` 的 `create_app()` 末尾调用 `seed_permissions()`。

## 验证

修复后验证：
1. admin 用户调用带 `@permission_required` 的接口 → 200 ✅
2. 普通用户调用相同接口 → 403（权限不足）✅
3. 非 admin 角色（assistant, doctor 等）的权限应只包含其需要的权限，不需要全部权限

## 关键区别

| 检查方式 | 数据来源 | 是否持久化 | 
|---------|---------|-----------|
| `g.roles` (JWT token) | Token payload | 24h 有效期 |
| `check_permission()` | Permission 表 + role_permissions 关联 | 持久化在 DB |

`@permission_required` 使用后者，所以 **Permission 表和关联必须有数据** 才能工作。这与前端角色显示（从 localStorage 的 roles 字段读取）是完全不同的机制。
