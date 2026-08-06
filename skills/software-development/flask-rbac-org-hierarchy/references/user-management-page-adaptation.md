# 用户管理页面适配（PC 管理端 page-admin-users.js）— 膏方 V2 实战 2026-08-06

给用户管理页加「小组分配」，适配新 RBAC + 组织架构权限体系。与 `frontend-permission-adaptation.md`（移动端 PWA）互补，本篇是 PC 管理端。

## 后端契约（改动后）

- `register_user(username, password, email=None, phone=None, full_name=None, role_id=None, group_id=None)` — 校验小组存在后写入 `user.group_id`
- `update_user(user_id, data)` — data 可含 `group_id`：`None/''/0` → 清空小组；否则 `Group` 查不到返回 400「小组不存在」
- `User.to_dict()` 已含 `group_id` + `group_name`（列表直接可用，无需 join）
- 小组/范围 API（api/v1/group.py，权限点 `group:*` / `director_scope:manage`）：
  - `GET /api/groups` — 列表，每项含 `members[]`（id/username/full_name/status）
  - `POST /api/groups` `{name, description}`；`PUT/DELETE /api/groups/<id>`（删除前须清空成员，否则 400）
  - `POST/DELETE /api/groups/<id>/members` `{user_ids: []}` — 批量加入/移出（DELETE 也带 JSON body，后端 `request.get_json()` 正常解析）
  - `GET /api/directors/<user_id>/scope` → `{user_id, group_ids, groups}`；`PUT .../scope` `{group_ids: []}` 全量覆盖

## ⚠️ 405 陷阱：创建用户的正确端点

原前端 POST `/api/auth/users` —— **该路由不存在（只有 GET），一直 405，创建用户功能本来就是坏的**。正确端点：**`POST /api/auth/register`**（对应 `register_user`，权限 `user:create`）。改前端 URL 即可，后端不用动。

## 前端模式（原生 JS + Bootstrap，IIFE + `window.pageLoaders`）

- **权限检查**：`canAccess(perm)` = `window.app.checkPermission(perm)` || roles 含 `admin/super_admin/pharmacy_admin`（fallback 兼容 permissions 未写入 localStorage 的旧会话）
- **按钮按权限显隐**：小组管理按钮 `group:read`、创建用户按钮 `user:create`
- **小组下拉**：`loadGroupsForSelect(selectId, selectedGroupId)` 读 `/api/groups`，`value=group.id`，空值 = 无小组
- **总监范围（编辑弹窗）**：用户 roles 含 `'director'` 才显示复选框区；并行 `GET /api/groups` + `GET /api/directors/<id>/scope` 回填勾选；保存时收集 checked → `PUT scope`（全量覆盖，追加在用户 PUT 之后链式执行）
- **小组管理弹窗**：`Promise.all([GET /api/groups, GET /api/auth/users])` 并行加载；成员管理 = 全用户复选框，当前成员 id 串存按钮 `data-member-ids`，保存时 diff（toAdd/toRemove）→ 分别 POST/DELETE members；重命名 `prompt()`、删除 `confirm()` 保持原生风格
- **HTML 注入必须 escapeHtml**（组名/姓名进 innerHTML 和 data 属性，防 XSS + 引号破坏属性）

## ⚠️ SPA 重复事件绑定

common.js 的 `loadLazyPageContent` 每次切 tab 都会重跑 `pageLoaders[pageName]()`，但模板只注入一次（`data-rendered` 属性）→ `bindEvents()` 每次执行导致监听器叠加、表单双提交。修复：

```js
var eventsBound = false;
function bindEvents() {
    if (eventsBound) return;  // 防止重复绑定
    eventsBound = true;
    ...
}
```

## 验证：权限接口免密码测试（Flask test client）

不知道 admin 密码也能全量测权限接口 —— 直接造 token：

```python
from app import app
from auth import generate_token
client = app.test_client()
with app.app_context():
    token = generate_token(user_id=1, username='admin', roles=['admin', 'super_admin'])
H = {'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json'}
```

- admin（user id=1）在 DB 里拥有全部权限点（`user:*` / `group:*` / `director_scope:manage`）→ 一条 token 测所有接口
- 临时数据用时间戳命名（`test_tmp_<ts>` / `测试组_<ts>`），测完 DELETE 清理
- **坑**：临时用户若配过 director scope，删用户前先 `PUT scope {group_ids: []}` 清空，否则外键报错
- 收尾确认无残留：`su - postgres -c "psql -d gaofang_v2 -t -c \"SELECT id,username FROM users WHERE username LIKE 'test_tmp%'; SELECT id,name FROM groups WHERE name LIKE '测试组%';\""`

## patch 工具陷阱（大段 HTML）

patch 模糊匹配大段 HTML 时可能只替换**部分区域**、把残留行留在文件尾部（本次 editUserModal 被替换成 groupManageModal 后尾部残留未匹配的 label/div）。大段 HTML 改动**优先 write_file 整体重写**；用 patch 则改完必须 `read_file` 全文复查。改动后验证：`node --check`（JS）+ `python3 -m py_compile`（py）+ 标签配对脚本（div/form/table 各 open==close，`input` 是 void 元素不算 mismatch）。
