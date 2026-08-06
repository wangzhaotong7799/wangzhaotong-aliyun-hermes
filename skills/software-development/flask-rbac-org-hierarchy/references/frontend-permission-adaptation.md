# 前端(PWA)权限适配实战 — 膏方V2 移动端（2026-08-06）

后端组织架构 RBAC 已上线（数据范围过滤 `get_visible_scope` + 领导层只读写接口 403 + 剂型/医生字段 `can_view_field` 置 None）。本次只改移动端 PWA 前端 6 个文件，后端零改动。

## 改动清单（可作同类任务模板）

| 文件 | 改动 |
|------|------|
| `static/mobile/js/store.js` | 新增 `getRoles()/setRoles()`（独立 key `mobile_roles`，回退 user 对象）+ `hasRole/hasAnyRole/isLeadership/canViewSensitive/canWrite`；`clearToken()` 清理 mobile_roles；`isGuest()` 收口到 getRoles（原只读 user 对象，双数据源不一致） |
| `static/mobile/js/api.js` | `login()` 与 `guestLogin()` 成功后补 `Store.setRoles(data.roles \|\| [data.role])` |
| `static/mobile/js/page-followup.js` | `fuActionButton()` 开头 `if (Store.isLeadership()) return '';`（隐藏复诊1/2/3 写按钮；停服/已停药状态灯保留） |
| `static/mobile/js/page-pickup.js` | `canEditAssistant = !Store.isLeadership() && user.username === 'yizhu001'`（详情弹窗编辑医助入口） |
| `static/mobile/js/page-reminders.js` | `showMarkBtn = !Store.isLeadership() && status 非已回访/已停服`（隐藏「标记已回访」按钮） |
| `static/mobile/index.html` + `sw.js` | 改动 JS 的 `?v=` 递增；`CACHE_NAME` v3→v4 |

## 排查顺序（先验证再动手）

1. **敏感字段 grep**：`grep -n 'doctor\|prescription_type\|剂型\|医生' static/mobile/` → 零匹配，移动端从未渲染剂型/医生 → 隐藏逻辑零改动（后端已兜底置 None）
2. **写入口枚举**：followup 复诊1/2/3 按钮、reminders 标记已回访、pickup 弹窗编辑医助 —— 3 个页面各一处，逐一加只读守卫
3. **确认后端已拦截**：`follow_up_management.py:474`、`prescriptions.py:368/449/558`、`excel.py:19` 均对 leadership 返回 403 → 前端隐藏仅为 UX，不是安全边界
4. **导航/菜单**：底部导航仅 膏方领取/复诊/提醒（无导入导出入口），领导层三页均可看 → 无需改导航

## 无头验证浏览器 JS（localStorage shim）

```javascript
const store = {};
global.localStorage = {
  getItem: (k) => (k in store ? store[k] : null),
  setItem: (k, v) => { store[k] = String(v); },
  removeItem: (k) => { delete store[k]; }
};
const fs = require('fs');
const vm = require('vm');
vm.runInThisContext(fs.readFileSync('store.js', 'utf8'));
// 断言 Store.hasRole('leadership') / Store.isLeadership() / Store.canWrite() ...
```

⚠️ **不要用 `eval()` 加载模块**：文件里 `const Store = ...` 声明在 eval 作用域内不泄漏，`eval(...)` 后调用 `Store` 报 ReferenceError，必须 `vm.runInThisContext`。每个改动文件先 `node --check` 过语法。

## 领域要点（膏方V2 权限现状）

- 角色：`super_admin / pharmacy_admin / leadership / director / group_leader / assistant / guest`
- 登录接口 `/api/auth/login` 与 `/api/auth/guest-login` 响应均含 `roles` 数组
- 领导层账号：GJD-A（赖总）、GJD-B（杨院）—— 用户名是 GJD-*，靠 roles 判断而非用户名
- `yizhu001` 已改名 `zj001`（总监）；前端 pickup 弹窗「编辑医助」仍是 `username === 'yizhu001'` 硬编码（旧逻辑未动，仅加只读守卫）—— 后续可考虑改为角色判断
- 药局管理员可编辑的字段（剂型/医生）在移动端不展示，桌面端按 `checkPermission('prescription_type:view'/'doctor:view')` 控制
