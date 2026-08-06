# 膏方V2 权限架构重构（2026-08-06）

组织架构级 RBAC：小组/门店 + 总监范围 + 字段级权限。设计文档存档于项目
`docs/权限架构重新设计方案_v1.md`，迁移脚本 `scripts/migrate_permissions_v1.sql`。

## 1. 组织模型（全动态，不硬编码账号）

```
超级管理员 admin
└── 药局管理员 yaoju001/yaoju002（可分配权限，唯一可见剂型+医生字段）
    ├── 领导层 GJD-A 赖总、GJD-B 杨院 —— 看全部数据，纯只读（列表+详情）
    ├── 总监 zj001（原 yizhu001 曹莹莹）→ 全部小组
    ├── 总监 zj002 张淇翔（新建）→ 康安路店+宝宇店+先锋路店（不含一组）
    ├── 组长（暂未设）→ 本组所有组员
    └── 医助 17人 → 一组，只看自己名下
```

小组共 4 个：**一组**（现有 17 医助：yizhu002~017 + cw001）、**康安路店**、**宝宇店**、**先锋路店**（后三者暂无成员，后续由药局管理员在界面挂人）。

## 2. 新增表结构

```sql
CREATE TABLE groups (                       -- 小组表
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL,       -- 一组/康安路店/宝宇店/先锋路店
    description VARCHAR(200),
    created_at TIMESTAMP DEFAULT now(),
    updated_at TIMESTAMP DEFAULT now()
);

CREATE TABLE director_group_scope (         -- 总监可见小组范围（多对多）
    user_id INT NOT NULL REFERENCES users(id),
    group_id INT NOT NULL REFERENCES groups(id),
    created_at TIMESTAMP DEFAULT now(),     -- 注意：模型有 created_at，SQL 必须同步建
    PRIMARY KEY (user_id, group_id)
);

ALTER TABLE users ADD COLUMN group_id INT REFERENCES groups(id);  -- 用户挂组
```

⚠️ **新表必须给应用用户授权**（postgres 建的默认 gaofang_app 无权限）：
```sql
GRANT SELECT, INSERT, UPDATE, DELETE ON groups, director_group_scope TO gaofang_app;
GRANT USAGE ON SEQUENCE groups_id_seq TO gaofang_app;
```

## 3. 角色与权限点

roles 新增：`super_admin`（admin）、`pharmacy_admin`（yaoju001/002）、`leadership`（GJD-A/B）、`director`（zj001/zj002）、`group_leader`；`assistant` 保留。

permissions 新增 12 个点：`group:create/read/update/delete`、`director_scope:manage`、
`data:all`、`data:read`、`data:write`、`data:export`、`data:import`、
`prescription_type:view`（剂型）、`doctor:view`（医生）。

分配：super_admin/pharmacy_admin=全部权限；leadership=data:all+data:read；
director=data:read+data:write+data:export；group_leader/assistant=data:read+data:write。

## 4. 核心后端逻辑（auth.py 新增）

```python
def get_visible_scope(user_id=None):
    """None=全部；[str,...]=可见医助姓名列表。
    优先级 super_admin > pharmacy_admin > leadership > director > group_leader > assistant"""
    # director → director_group_scope 查小组 → 组内 active 用户 full_name+username
    # group_leader → users.group_id == 本组 → 组内成员
    # assistant → [自己 full_name or username]
```

统一过滤助手 `_apply_scope_filter(query, model)`：scope 为 None 不过滤；否则
`assistant IN scope OR assistant IS NULL/''/'-'`。处方表 `assistant` 字段存 **full_name**（姓名），
_get_collect_names 同时收集 full_name+username 双匹配（yizhu010 无 full_name 用 username 兜底）。

字段级权限 `_mask_sensitive_fields(d)` + `can_view_field('prescription_type'/'doctor')`：
无权限时 prescription_type/doctor 置 None。已接入：列表、详情、创建、更新、统计、Excel 导出（动态列）。

领导层只读拦截：prescriptions 的 POST/PUT/DELETE/import、复诊 update/stop 开头
`'leadership' in payload['roles'] → 403`。

## 5. 用户变更

- `yizhu001` 改名 `zj001`（保留密码/角色，处方表 assistant 存的是姓名曹莹莹不受影响）
- 新建 `zj002` 张淇翔，临时密码 `Zj002@123456`（bcrypt 哈希已入库，主人可改）
- 17 医助 UPDATE users SET group_id=一组；总监范围经 director_group_scope 配置

## 6. 前端改动（已完成部分）

- common.js：登录后 fetch `/api/auth/me` 拉 permissions 存 localStorage；
  `checkPermission()` 真实检查权限点；导航显隐按 super_admin/pharmacy_admin/leadership 分级；
  领导层隐藏导入/导出/打印按钮
- page-prescriptions.js：剂型/医生列按 `prescription_type:view`/`doctor:view` 显隐；
  编辑弹窗领导层拦截；剂型/医生字段按权限禁用

## 7. 待办/已知未完成

- `page-admin-users.js` 未完成小组分配 UI（用户管理页需能改 group_id、配总监范围）
- 前端 /api/auth/me 需确认返回 permissions 数组（get_user_info 已含）
- 复诊模块 PWA（static/mobile/）权限显隐未同步改
- admin-users 页面 admin 角色判断需含 super_admin/pharmacy_admin

## 8. 陷阱记录

1. **GRANT 权限**：新表未授权 → `InsufficientPrivilege: permission denied for table groups`
2. **模型/SQL 字段不一致**：DirectorGroupScope 模型有 created_at 但 SQL 表没有 → `UndefinedColumn`；迁移 SQL 与 models/*.py 必须逐字段对齐
3. **硬编码账号残留**：复诊模块 `SPECIAL_ACCOUNTS=['yizhu001','GJD-A','GJD-B']` 与 prescriptions.py 的同类名单已全部移除；以后新增模块不得再用账号名判断权限
4. JWT roles 是登录快照，改角色/改名后需重新登录
5. Gunicorn 改代码后需清 __pycache__ 并重启（多 worker 缓存）

## 9. ⚠️ 端到端测试发现（2026-08-06，重要状态更新）

**重构代码存在致命回归，API 层 scope/脱敏未生效**，勿假设上文"已接入"即工作正常：

- `prescriptions.py` 全部 7 个路由与 `follow_up_management.py` 全部 5 个路由**缺 `@auth_required`** → `g.user_id` 从未注入 → `get_visible_scope()` 返回 None（**所有用户含医助都拿到全量 4385 条**）、`can_view_field()` 恒 False（**连 admin/yaoju001 也看不到剂型/医生**）
- 同一根因导致**匿名可读写**：无 token POST 新建 201 真实入库、GET 详情 200、DELETE 200 成功
- 复诊 `/api/follow-up`：admin 与医助均 408 条（scope 未生效）
- **正常对照**：stats.py / excel.py 有 `@auth_required`，scope 与权限均正确（admin=4385 vs yizhu003=963；GJD-A 导出 403）
- 修复：给上述路由补 `@auth_required`（先确认游客场景）；完整测试方法/脚本与回归用例见 `flask-rbac-org-hierarchy` 技能 `references/e2e-permission-testing.md`
- 数据一致性：处方表 assistant='张春梅' 100 条 与用户表 yizhu009='张冬梅' 不符 → 总监/组长范围看不到这 100 条（数据问题，非代码问题）
