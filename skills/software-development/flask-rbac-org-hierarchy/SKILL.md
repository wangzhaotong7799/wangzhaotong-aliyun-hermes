---
name: flask-rbac-org-hierarchy
description: "Flask 组织架构型 RBAC 权限模型设计 — 角色×数据范围双层模型、小组行级权限、硬编码账号/角色判断的统一改造"
version: 1.0.0
author: Hermes Agent
tags: [flask, rbac, permission, org-hierarchy, row-level-access, group, python]
toolsets_required: ['terminal', 'file']
category: software-development
metadata:
  hermes:
    tags: [flask, rbac, permission, org-hierarchy, row-level-access, group, python]
  applicability: flask-apps-with-org-permission-redesign
  priority: high
---

# 🏛️ Flask 组织架构型 RBAC 权限模型

## 🎯 适用场景

当用户要求把 Flask 应用的权限从"扁平角色"升级为"组织架构"时使用：

- 角色分层：超级管理员 → 管理员 → 领导层 → 总监 → 组长 → 组员
- 数据按**小组**归属，不同角色/总监只能看部分小组的数据（行级权限）
- 现有代码是硬编码账号白名单（如 `SPECIAL_ACCOUNTS = ['yizhu001','GJD-A']`）或字符串角色判断（`'admin' in g.roles`），需要统一

## 🔑 核心设计原则：两层分开建模

1. **角色 = 功能权限**（能做什么：增删改查、管理用户）
2. **小组 = 数据范围**（能看到谁的数据：行级过滤）

不要混在一个字段里。角色走 RBAC 表（User/Role/Permission），小组走组织表（groups）。

## 🏗️ 数据模型

```
groups(id, name)                          # 小组表
users.group_id                            # 用户挂组（外键）
director_groups(user_id, group_id)        # 总监级"部分小组"范围（多对多）
# 或 users.visible_group_ids (JSON 字段)  # 简单场景可替代关联表
```

- 总监A看全部组 → 不配 director_groups 行，语义 = 全量
- 总监B看组3+4 → 配两行 director_groups
- 组长 → 取 users.group_id 单组
- 组员 → 只看自己名下（assistant == 自己姓名）

## 🔌 数据归属映射（关键陷阱）

业务表通常存**负责人姓名/字符串**（如 `prescription_records.assistant = '曹莹莹'`），不是 user_id。

行级过滤的桥梁必须是：`业务表.姓名 ↔ users.full_name` → `用户.group_id` → 组范围。

**先验证姓名可关联**（同名、空值、'-' 占位、历史人员不在 users 表等情况），否则过滤会漏数据或全空。

## 🧰 统一封装行级过滤

```python
def get_visible_scope(user) -> set[int] | None:
    """None = 全部；否则 = 可见 group_id 集合"""
    roles = [r.name for r in user.roles]
    if 'super_admin' in roles or 'pharmacy_admin' in roles or 'leadership' in roles:
        return None
    if 'director' in roles:
        return {g.group_id for g in director_groups(user.id)}  # 空集=无
    if 'group_leader' in roles:
        return {user.group_id}
    # 组员：不返回组，查询时用 assistant == 自己姓名
    return set()
```

所有业务查询接口共用这一个函数，替换散落的硬编码。

## ⚠️ 动工前必须确认（问题声明铁律）

先出**方案 + 问题清单**，等主人逐条答复再动工，不要擅自脑补：

1. 组长能看什么？本组全部 or 仅自己名下
2. 组员能看什么？仅自己 or 本组
3. 领导层定位：看全部数据，只读？
4. 现有用户如何映射到新组；原硬编码特殊账号（yizhu001/GJD-A/GJD-B 等）归为总监还是领导层

## 🚨 常见陷阱

| 问题 | 解决方案 |
|------|---------|
| 硬编码账号白名单散落各模块 | 统一收敛进 `get_visible_scope`，删除 SPECIAL_ACCOUNTS |
| "部分小组"范围判断写成 == | 用集合运算（并集/包含），不是简单相等 |
| 改权限后服务不生效 | Gunicorn 重启 + 清 `__pycache__`：`find . -name __pycache__ -exec rm -rf {} +` 后 `fuser -k <port>/tcp` 重启 |
| 项目内 search_files 返回空 | 该项目用 terminal grep：`grep -rn "关键词" --include="*.py" . \| grep -v venv38`（venv38 必须排除） |
| 业务表姓名无法关联用户 | 先查重名/空值/'-'占位，再决定过滤键 |
| 创建用户 405（膏方V2） | 前端别 POST `/api/auth/users`（无此路由），用 `POST /api/auth/register`（对应 register_user，权限 user:create） |
| SPA 切 tab 后表单双提交/事件叠加 | `pageLoaders` 每次切页都重跑但模板只注入一次 → `bindEvents()` 用 `eventsBound` 标志防重 |
| patch 大段 HTML 只替换了部分、尾部残留 | 大段 HTML 改动优先 write_file 整体重写；patch 后必须 read_file 全文复查 |
| 重构后全员可见全量数据 + 连 admin 也被脱敏 | 路由缺 `@auth_required` → `g.user_id` 未注入 → `get_visible_scope()` 返回 None(不过滤)、`can_view_field()` 返回 False(全员脱敏)。旧代码常在路由内手动 `verify_token` 解析 token（如 `_get_assistant_name_from_token`），换成依赖 `g` 的统一函数后**必须给每条路由补 `@auth_required`** |
| 匿名可读写（POST/DELETE 无需登录即可增删数据） | 同一根因：无 `@auth_required` 的路由对匿名开放。补装饰器时一并封死；先确认游客/guest 场景是否要保留 |
| 直调函数正常 ≠ 接口生效 | 验证必须走 API 层：`get_visible_scope(user_id)` 直调 OK 但接口返回全员同量数据 → 定位为认证注入问题（g.user_id 未设置）；反向用带 `@auth_required` 的模块（如 stats）验证 scope 逻辑本身正确。完整测试方法见 `references/e2e-permission-testing.md` |

## 🖥️ 前端适配（PWA/SPA 权限动态显隐）

后端落地后，前端按角色动态显隐（本会话实战：膏方 V2 移动端 PWA，后端零改动）：

1. **角色存储**：登录响应 `roles` 数组存独立 localStorage key（对齐 PC 端 `localStorage['roles']` 做法）；`getRoles()` 回退兼容旧 user 对象（`user.roles`/`user.role`），否则老用户要重新登录才生效
2. **集中 helper**：store.js 提供 `hasRole/hasAnyRole/isLeadership/canWrite`，页面只调 helper 不裸判角色
3. **⚠️ 双数据源陷阱**：新增独立 roles key 后，旧判断（如 `isGuest()` 只读 user 对象）会与 roles key 不一致 —— 所有角色判断（含 isGuest）统一走 `getRoles()`
4. **先 grep 再改敏感字段**：后端 `can_view_field()` 已把剂型/医生置 None 时，先 `grep 'doctor\|prescription_type\|剂型\|医生'` 确认前端是否真渲染；零匹配 = 零改动，不为不存在的问题写代码
5. **领导层只读 = 逐页隐藏写入口**：grep 枚举全部写入口（列表操作按钮/卡片标记按钮/弹窗编辑区）逐一加 `!isLeadership()` 守卫；后端已 403，前端隐藏只是 UX 同步（保留状态 badge/状态灯，只去掉可点击按钮）
6. **数据范围参数前端不要重复传**（`assistant=xxx` 会与后端 JWT 过滤 AND 叠加误过滤）
7. **无头验证浏览器 JS**：`node --check` + localStorage shim + `vm.runInThisContext()`（⚠️ `eval()` 里的 `const` 不泄漏到外层作用域，直接 eval 加载模块会 ReferenceError）

**PC 管理端（用户/小组管理页）另有一套模式**：用户列表加 `group_name` 列、编辑弹窗小组下拉 + 总监范围复选框（仅 director 角色显示）、小组管理弹窗（成员复选框 diff → POST/DELETE members）、`eventsBound` 防 SPA 切 tab 重复绑事件、权限接口免密码测试（`generate_token` + Flask test client）。详见 `references/user-management-page-adaptation.md`。

实战细节见 `references/frontend-permission-adaptation.md`（膏方V2 PWA 改动清单 + 验证脚本）。

## 📁 参考文件

| File | Content |
|------|---------|
| `references/gaofang-v2-permission-redesign.md` | 膏方V2 实际改造案例：现状基线、目标架构图、待确认问题、实现路径 |
| `references/frontend-permission-adaptation.md` | 前端(PWA)权限适配实战：角色存储、只读守卫位置、无头验证脚本 |
| `references/user-management-page-adaptation.md` | PC 管理端用户/小组管理页适配：group_id 后端契约、总监范围 UI、405 register 端点、eventsBound 防重绑、免密码 test-client 验证 |
| `references/e2e-permission-testing.md` | 权限改造端到端测试方法：API 层验证技巧、SQL 期望值口径、写测试还原/清理、膏方V2 实测发现与修复建议 |
