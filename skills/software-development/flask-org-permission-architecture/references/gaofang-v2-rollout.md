# 膏方系统权限架构改造落地记录（2026-08）

真实项目：`/workspace/projects/drug-distribution-system/gaofang-v2`（Flask + PostgreSQL + SQLAlchemy）

## 需求背景

医院膏方管理系统，组织架构：

```
超级管理员 admin
└── 药局管理员 yaoju001/002（可分配权限，唯一可见剂型+医生）
    ├── 领导层 GJD-A/B（看全部，纯只读）
    ├── 总监 zj001（全部小组）/ zj002（3门店）
    ├── 组长（本组）/ 医助（自己）
```

4 小组：一组（17医助）、康安路店、宝宇店、先锋路店。

## 表结构增量

```sql
CREATE TABLE groups (
    id SERIAL PRIMARY KEY, name VARCHAR(50) UNIQUE NOT NULL,
    description VARCHAR(200), created_at TIMESTAMP DEFAULT now(), updated_at TIMESTAMP DEFAULT now()
);
CREATE TABLE director_group_scope (
    user_id INT NOT NULL REFERENCES users(id),
    group_id INT NOT NULL REFERENCES groups(id),
    PRIMARY KEY (user_id, group_id)
);
ALTER TABLE users ADD COLUMN group_id INT REFERENCES groups(id);
```

角色：super_admin / pharmacy_admin / leadership / director / group_leader / assistant
权限点：user:*/role:*/group:*/director_scope:manage / data:all / data:read / data:write / data:export / data:import / prescription_type:view / doctor:view

## 用户初始化（密码规则 = 用户名+123456）

店长/文员 → `group_leader`（看全店），医助 → `assistant`（看自己）。
总监范围：`INSERT INTO director_group_scope (user_id, group_id) SELECT u.id, g.id FROM users u CROSS JOIN groups g WHERE u.username='zj002' AND g.name IN ('康安路店','宝宇店','先锋路店');`

## 字段级权限实现

- 权限点 `prescription_type:view` / `doctor:view` **只分配给** super_admin / pharmacy_admin
- 后端 `_mask_sensitive_fields(d)`：无权限 → `d['prescription_type'] = None; d['doctor'] = None`
- 统计接口 doctor/type 统计无权限时返回空数组
- 导出 Excel：无权限时不输出这两列（表头和数据行同步过滤）

## 领导层只读实现

每个写接口（create/update/delete/import/follow-up update/stop/reminders update）开头：

```python
if payload and 'leadership' in payload.get('roles', []):
    return jsonify({"error": "领导层为只读权限，无法修改数据"}), 403
```

## 验证清单（改动后必跑）

1. `./venv38/bin/python -c "from app import create_app; app = create_app(); print('OK')"` 应用启动
2. `get_visible_scope()` 各角色：admin=None、yaoju=None、GJD-A=None、zj001=全部、医助=自己
3. `can_view_field('prescription_type', uid)`：admin/yaoju=True，其余 False
4. 匿名请求 `GET/POST/DELETE /api/prescriptions` → 401（无 @auth_required 时的漏洞检查）
5. 店长 PUT 状态 → 200；店长 PUT 剂型 → 被拦截；纯医助 PUT 状态 → 状态不变
6. 登录验证（admin 密码 admin123，其他 = 用户名+123456）

## 前端文件清单

- `static/js/common.js` — 导航显隐（updateLoginStatus）、permissions 存 localStorage
- `static/js/page-prescriptions.js` — 列显隐 + 编辑弹窗字段控制
- `static/js/page-followup.js` — 复诊页敏感列 + 医助搜索（必须 fetchWithAuth 带 token）
- `static/js/page-admin-users.js` — 用户管理 + 小组管理弹窗 + 总监范围配置
- `templates/admin-users.html` — 小组管理 UI
- `static/mobile/js/store.js` — 移动端角色存储 + isLeadership/canWrite/canViewSensitive
- 移动端写按钮：`!Store.isLeadership()` 才显示

## 遗留注意

- 用户/角色是数据库读取无缓存，改库即时生效；改代码需清 __pycache__ + HUP 重启
- 历史处方表 assistant 字段存姓名，与 users.full_name 匹配；新用户无历史数据时总监/店长看不到门店客户（数据问题非权限问题）
- 删除旧角色 admin/pharmacy/yaoju 后，前端 page-admin-roles.js 的 `roles.indexOf('admin') === -1` 守卫必须同步改为 super_admin/pharmacy_admin，否则 admin 打不开角色管理页
