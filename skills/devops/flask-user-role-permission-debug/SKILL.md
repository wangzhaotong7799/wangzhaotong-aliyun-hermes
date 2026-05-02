---
name: flask-user-role-permission-debug
title: Flask 用户角色权限故障排查
description: 排查 Flask 应用中 user_roles 中间表为空、角色批量分配、参数名不匹配等权限系统故障
tags:
  - flask
  - permissions
  - debugging
  - user-roles
  - postgresql
---

# Flask 用户角色权限故障排查

## 适用场景

- 管理员登录后看不到管理功能导航项
- 用户登录后 API 返回 `403 Forbidden` 即使角色配置看似正确
- 医助能看到所有患者的数据（应该只能看到自己的）
- 打印/备份/恢复等功能返回权限错误
- API 返回列表格式而非分页格式

## 问题 1: `user_roles` 中间表为空

### 现象

所有症状都指向"权限系统静默失效"：

| 表现 | 为什么 |
|------|--------|
| admin 看不到管理导航 | `updateLoginStatus()` 中 `hasAdmin = false` ← roles=`[]` |
| 医助看到所有数据 | 后端 `_apply_assistant_filter()` 检查 `'assistant' in roles` 永远 false |
| 打印/备份返回 403 | 后端角色检查 `if 'admin' not in g.roles` 永远 true |

**登录响应本身就暴露了问题：**
```bash
curl -s -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"admin123"}' \
  http://localhost:8080/api/auth/login

# 返回：
{ "roles": [], "token": "..." , ...}
#          ^^ 空数组是信号！
```

### 根因

`user_roles` 中间表为空。用户在 `users` 表中有记录，角色在 `roles` 表中有定义，但二者的关联（`user_roles` 表）缺失。

**常见触发场景：**
- 从 SQLite 迁移到 PostgreSQL 后，关联关系未迁移
- 用户是批量导入的（如 `batch_create_assistant_users.py`），但角色分配步骤被跳过
- 数据库从备份恢复，但 `user_roles` 数据未包含在备份中

### 诊断命令

```bash
# 查看所有用户的角色状态（30秒定位）
psql -U gaofang_app -d gaofang_v2 -c "
SELECT u.id, u.username, u.full_name,
       ur.role_id, r.name AS role_name
FROM users u
LEFT JOIN user_roles ur ON u.id = ur.user_id
LEFT JOIN roles r ON ur.role_id = r.id
ORDER BY u.id;
"

# 嫌疑输出 — role_id 和 role_name 全是 NULL
#  id | username | full_name  | role_id | role_name
# ----+----------+------------+---------+-----------
#   1 | admin    | 系统管理员 |         |
#  27 | yizhu001 | 曹莹莹     |         |
```

### 修复方法

**方法一：单个用户分配**
```sql
INSERT INTO user_roles (user_id, role_id)
SELECT u.id, r.id FROM users u, roles r
WHERE u.username = 'admin' AND r.name = 'admin';
```

**方法二：按命名规则批量分配**
```sql
-- 所有 yizhu* 用户 → assistant 角色
INSERT INTO user_roles (user_id, role_id)
SELECT u.id, r.id FROM users u, roles r
WHERE u.username LIKE 'yizhu%' AND r.name = 'assistant';

-- yaoju* 用户 → yaoju 角色
INSERT INTO user_roles (user_id, role_id)
SELECT u.id, r.id FROM users u, roles r
WHERE u.username LIKE 'yaoju%' AND r.name = 'yaoju';

-- 特殊管理员账号
INSERT INTO user_roles (user_id, role_id)
SELECT u.id, r.id FROM users u, roles r
WHERE u.username IN ('GJD-A', 'GJD-B') AND r.name = 'assistant';
```

**方法三：全部角色都有（通用脚本）**
```python
import psycopg2

conn = psycopg2.connect(
    host='localhost', dbname='gaofang_v2',
    user='gaofang_app', password='your_password'
)
cur = conn.cursor()

assignments = {
    'admin': ['admin'],
    'yizhu001': ['assistant'],
    'GJD-A': ['assistant'],
    'GJD-B': ['assistant'],
    'yaoju001': ['yaoju'],
    'yaoju002': ['yaoju'],
}

for username, role_names in assignments.items():
    for role_name in role_names:
        cur.execute("""
            INSERT INTO user_roles (user_id, role_id)
            SELECT u.id, r.id FROM users u, roles r
            WHERE u.username = %s AND r.name = %s
            ON CONFLICT DO NOTHING
        """, (username, role_name))

conn.commit()
```

### 验证修复

```bash
curl -s -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"admin123"}' \
  http://localhost:8080/api/auth/login | python3 -c "
import sys,json
d=json.load(sys.stdin)
print(f'roles={d.get(\"roles\",[])}')
# 修复前: roles=[]
# 修复后: roles=['admin']
"
```

## 问题 2: 未知或遗忘的密码

### 诊断

查出所有用户的密码哈希格式，确认 bcrypt 加密：
```bash
psql -U gaofang_app -d gaofang_v2 -c "SELECT username, password_hash FROM users;"
```

### 批量重置密码

格式统一为 `用户名+123`（如 `yizhu003` → 密码 `yizhu003123`）：

```python
import bcrypt
import psycopg2

conn = psycopg2.connect(
    host='localhost', dbname='gaofang_v2',
    user='gaofang_app', password='your_password'
)
cur = conn.cursor()

cur.execute("SELECT id, username FROM users WHERE username LIKE 'yizhu%'")
for uid, uname in cur.fetchall():
    pw = uname + '123'
    hashed = bcrypt.hashpw(pw.encode('utf-8'), bcrypt.gensalt())
    cur.execute("UPDATE users SET password_hash=%s WHERE id=%s",
                (hashed.decode('utf-8'), uid))

# 特殊账号单独处理
for uname, pw in [('admin', 'admin123'), ('yaoju001', 'yaoju001123')]:
    hashed = bcrypt.hashpw(pw.encode('utf-8'), bcrypt.gensalt())
    cur.execute("UPDATE users SET password_hash=%s WHERE username=%s",
                (hashed.decode('utf-8'), uname))

conn.commit()
```

## 问题 3: 后端 API 参数名不匹配

### 现象

前端传 `?page=1&per_page=50`，但 API 返回列表格式而非分页格式：
```bash
curl -s 'http://localhost:8080/api/prescriptions?page=1&per_page=1' | head -c 50
# `[{...`  → 列表格式（非分页！）
# `{"data":` → 分页格式 ✓
```

### 原因

后端代码用 `request.args.get('page_size', type=int)` 读取，但前端传的是 `per_page`。

### 修复

```python
# ❌ 只读 page_size，永远收不到 per_page
page_size = request.args.get('page_size', type=int)

# ✅ 同时兼容两种参数名
page_size = request.args.get('per_page', type=int) or request.args.get('page_size', type=int)
```

## 问题 4: `permissions` 表为空导致 `@permission_required` 返回 403

### 现象

所有用户（包括 admin）访问带有 `@permission_required('user:read')` 装饰器的 API（如 `/api/auth/users`）都返回 403 `权限不足`。**这与 `user_roles` 为空的表现不同**——登录后 JWT 中的 roles 正常返回（比如 `['admin']`），但具体 API 仍然 403。

前端控制台显示：
```
GET /api/auth/users 403 (FORBIDDEN)
fetchWithAuth @ common.js:79
```

### 与问题 1 (`user_roles` 为空) 的对比

| 问题 | 表现 | 原因 |
|------|------|------|
| `user_roles` 为空 | 登录后 roles=`[]`，前端导航消失 | JWT 直接存了 roles 列表（登录时从 user_roles 表查），空列表就无权限 |
| `permissions` 为空 | 登录后有 roles，但 `@permission_required` API 返回 403 | 装饰器实时查数据库 `check_permission()`，找不到权限记录 |

**关键诊断线索：** 如果 admin 登录后能看到导航栏（表示 roles 非空），但 `/api/auth/users` 仍返回 403，那 90% 是 permissions 表的问题，而不是 user_roles。

前端控制台显示：
```
GET /api/auth/users 403 (FORBIDDEN)
fetchWithAuth @ common.js:79
```

### 根因

数据库的 `permissions` 表和 `role_permissions` 关联表完全为空。`@permission_required` 装饰器调用的 `check_permission()` 函数（第 228-245 行，auth.py）会实时查数据库：遍历用户角色的所有权限，如果找不到匹配项，返回 `False` → 403。

**常见触发场景：**
- 从 SQLite 迁移到 PostgreSQL 时，`permissions` 表和 `role_permissions` 关联表的数据未迁移
- 系统初始化时只创建了角色和用户，但没创建权限记录
- 数据库重建/重置后，权限数据丢失

### 诊断

```bash
# 检查权限表是否为空
psql -U gaofang_app -d gaofang_v2 -c "
SELECT p.id, p.name, p.description, rp.role_id, r.name AS role_name
FROM permissions p
LEFT JOIN role_permissions rp ON p.id = rp.permission_id
LEFT JOIN roles r ON rp.role_id = r.id
ORDER BY p.id;
"

# 嫌疑输出 — 空表
#  id | name | description | role_id | role_name
# ----+------+-------------+---------+-----------
# (0 rows)
```

```python
# 也可以用 Python 查
python3 -c "
from app import app
from database import db
from models import Role, Permission

with app.app_context():
    session = db.session
    admin_role = session.query(Role).filter_by(name='admin').first()
    print(f'admin角色: {admin_role}')
    print(f'admin权限: {[p.name for p in admin_role.permissions] if admin_role else \"N/A\"}')
    print(f'所有权限: {[p.name for p in session.query(Permission).all()]}')
"
```

### 修复

需要两步：1) 创建权限记录 2) 分配给角色

```python
from app import app
from database import db
from models import Role, Permission

with app.app_context():
    session = db.session

    # 1. 创建所有标准权限
    permissions_to_create = [
        ('user:read', '查看用户'),
        ('user:create', '创建用户'),
        ('user:update', '更新用户'),
        ('user:delete', '删除用户'),
        ('role:read', '查看角色'),
        ('role:create', '创建角色'),
        ('role:update', '更新角色'),
        ('role:delete', '删除角色'),
    ]
    
    for perm_name, perm_desc in permissions_to_create:
        existing = session.query(Permission).filter_by(name=perm_name).first()
        if not existing:
            session.add(Permission(name=perm_name, description=perm_desc))

    session.flush()

    # 2. 给 admin 角色分配所有权限
    admin_role = session.query(Role).filter_by(name='admin').first()
    if admin_role:
        all_perms = session.query(Permission).all()
        for p in all_perms:
            if p not in admin_role.permissions:
                admin_role.permissions.append(p)

    session.commit()
```

### 修复后验证

```bash
TOKEN=$(curl -s -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"admin123"}' \
  http://localhost:8080/api/auth/login | python3 -c \
  "import sys,json;print(json.load(sys.stdin).get('token',''))")

curl -s -o /dev/null -w "%{http_code}" \
  http://localhost:8080/api/auth/users \
  -H "Authorization: Bearer $TOKEN"
# 修复前: 403
# 修复后: 200
```

### 前端防护：页面加载器加前置角色检查

即使后端权限修复了，也推荐在三个管理页面的页面加载器（`pageLoaders`）中加一层前置角色检查，防止非管理员通过 URL hash 直接访问管理页面时触发 API 错误：

```javascript
// page-admin-users.js, page-admin-roles.js, page-admin-database.js
window.pageLoaders['admin-users'] = function() {
    if (!window.app.isLoggedIn()) {
        alert('请先登录');
        return;
    }
    var roles = window.app.getUserRoles();
    if (roles.indexOf('admin') === -1) {
        var loadingEl = document.getElementById('loading-users');
        var tableBody = document.getElementById('users-table-body');
        if (loadingEl) loadingEl.style.display = 'none';
        if (tableBody) {
            tableBody.innerHTML = '<tr><td colspan="9" class="text-center text-danger">⚠️ 无权限访问，仅管理员可用</td></tr>';
        }
        return;
    }
    bindEvents();
    loadUsers();
};
```

## 预防措施

1. **初始化脚本必须包含角色分配** — 创建用户后立即分配角色
2. **迁移脚本必须包含关联表** — SQLite→PostgreSQL 迁移时，`user_roles` 是独立表
3. **登录后立即验证 `roles`** — 前端打印 `console.log('roles:', data.roles)` 确认非空
4. **API 参数名统一** — 全项目统一用 `per_page` 或 `page_size`，不要混用
