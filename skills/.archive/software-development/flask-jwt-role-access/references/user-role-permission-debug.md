# Flask 用户角色权限故障排查

> 吸收自 `flask-user-role-permission-debug`（2026-05 合并）
> 本参考涵盖角色分配缺失、权限表空、参数名不匹配等权限系统故障的诊断与修复。

## 问题 1: `user_roles` 中间表为空

### 诊断

登录响应中 roles=`[]` 是信号。验证命令：

```bash
psql -U gaofang_app -d gaofang_v2 -c "
SELECT u.id, u.username, u.full_name,
       ur.role_id, r.name AS role_name
FROM users u
LEFT JOIN user_roles ur ON u.id = ur.user_id
LEFT JOIN roles r ON ur.role_id = r.id
ORDER BY u.id;
"
# 嫌疑输出：role_id 和 role_name 全是 NULL
```

### 修复：批量角色分配

```sql
-- 按用户名规则批量分配
INSERT INTO user_roles (user_id, role_id)
SELECT u.id, r.id FROM users u, roles r
WHERE u.username LIKE 'yizhu%' AND r.name = 'assistant';
```

## 问题 2: `permissions` 表为空导致 403

### 关键诊断线索

- 登录后 `roles` 正常（如 `['admin']`），但 `@permission_required` API 仍返回 403
- 原因：`@permission_required` 是**数据库运行时检查**，不是静态角色名检查
- `Permission` 表和 `role_permissions` 关联表必须播种

### 修复：播种权限

```python
with app.app_context():
    session = db.session
    perms = [Permission(name=n, description=d) for n, d in [
        ('user:read', '查看用户'), ('user:create', '创建用户'),
        ('role:read', '查看角色'), ('role:create', '创建角色'),
    ]]
    session.add_all(perms)
    session.flush()
    admin_role = session.query(Role).filter_by(name='admin').first()
    if admin_role:
        admin_role.permissions.extend(perms)
    session.commit()
```

## 问题 3: 后端 API 参数名不匹配

```bash
# 前端传 ?page=1&per_page=50，后端用 request.args.get('page_size')
# 修复：同时兼容两种参数名
page_size = request.args.get('per_page', type=int) or request.args.get('page_size', type=int)
```

## 预防措施

1. 创建用户后立即分配角色
2. 迁移脚本必须包含 `user_roles` 等关联表数据
3. 登录后前端验证 `console.log('roles:', data.roles)` 确认非空
4. 全项目统一参数名（`per_page` 或 `page_size` 择一）
