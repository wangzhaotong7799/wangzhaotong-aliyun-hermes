---
name: flask-jwt-role-access
description: JWT 角色权限管理 — 添加角色到 JWT 令牌、基于角色的数据过滤、端点访问控制，以及前端集成（角色检测、路由守卫、UI 隐藏）
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [flask, jwt, role, access-control, auth, pwa]
    related_skills: [flask-api-troubleshooting, flask-webapp-security-hardening, flask-user-role-permission-debug]
---

# Flask JWT 角色权限管理

## Overview

本技能覆盖如何向 Flask API 添加角色（role）级别的权限控制，包括：

1. **后端** — JWT 令牌中嵌入角色、创建限权登录端点、基于角色的数据过滤、端点级访问拦截  
2. **前端** — 角色检测、路由守卫、UI 隐藏/显示

**核心原则**: 后端必须做完整的权限检查（前端隐藏只是体验优化），避免「前端隐藏了按钮但 API 仍可调用」的安全漏洞。

---

## When to Use

| 场景 | 示例 |
|------|------|
| 需要不同用户看到不同数据（行级） | 医助只能看自己名下的处方 |
| 需要某些端点只对特定角色开放 | 游客不能复诊/提醒 |
| 需要加一个「只需要看」的受限角色 | 游客登录只显示未取 |
| 前端标签/按钮需要根据角色显示/隐藏 | 游客看不到复诊和提醒 tab |

---

## Backend Implementation

### Step 1: JWT Token 中加入角色

在 `auth.py` 或认证模块的 `generate_token` 函数中，确保 `roles` 字段在 payload 中：

```python
# auth.py
def generate_token(user_id, username, roles):
    secret = current_app.config.get('JWT_SECRET_KEY', 'default-secret')
    payload = {
        'user_id': user_id,
        'username': username,
        'roles': roles,                # ← 角色列表，如 ['guest'] 或 ['assistant', 'admin']
        'exp': datetime.utcnow() + timedelta(hours=24)
    }
    token = jwt.encode(payload, secret, algorithm='HS256')
    return token
```

### Step 2: 创建限权登录端点

对于「游客登录」等不需要密码的受限账号，创建一个专门的登录接口：

```python
# api/v1/auth.py
@auth_bp.route('/guest-login', methods=['POST'])
def guest_login():
    """游客登录（无需任何凭证，只能看未取处方）"""
    from auth import generate_token
    token = generate_token(user_id=0, username='guest', roles=['guest'])
    return jsonify({
        "message": "游客登录成功",
        "token": token,
        "username": "guest",
        "full_name": "游客",
        "role": "guest",
        "roles": ["guest"]
    }), 200
```

关键点：
- `user_id=0` 表示虚拟用户（不实际对应数据库记录）
- `roles=['guest']` 只有一个 role，后续所有权限判断基于此
- 返回格式与普通登录一致，前端可以直接复用 `Store.setUser()` 逻辑

### Step 3: 编写角色检测辅助函数

在每个需要角色判断的 API blueprint 中编写一个通用函数：

```python
# 在 followups.py / prescriptions.py 等文件中
def _check_guest_role():
    """从 token 中检查是否 guest 角色"""
    token = request.headers.get('Authorization')
    if token and token.startswith('Bearer '):
        token = token[7:]
        payload = verify_token(token)
        if payload and 'guest' in payload.get('roles', []):
            return True
    return False
```

可以泛化成一个更通用的版本：

```python
def _has_role(role_name):
    """检查当前 token 是否包含指定角色"""
    token = request.headers.get('Authorization')
    if token and token.startswith('Bearer '):
        token = token[7:]
        payload = verify_token(token)
        if payload and role_name in payload.get('roles', []):
            return True
    return False

# 使用
if _has_role('guest'): ...
if _has_role('admin'): ...
```

### Step 4: 基于角色的数据过滤（行级权限）

在查询时根据角色过滤结果：

```python
@prescriptions_bp.route('/prescriptions', methods=['GET'])
def get_prescriptions():
    query = session.query(PrescriptionRecord)

    # 游客只能看未取
    if _has_role('guest'):
        query = query.filter(PrescriptionRecord.status == '未取')

    # 医助数据隔离
    if _has_role('assistant'):
        assistant_name = _get_assistant_name()
        if assistant_name:
            query = query.filter(
                PrescriptionRecord.assistant.in_([assistant_name, None, '', '-'])
            )

    # 普通用户无限制
    # ...

    result = query.all()
```

⚠️ **注意优先级**: 如果多个角色叠加，需要确保过滤条件「叠加」而不是「覆盖」。上面的例子中 `guest` 和 `assistant` 角色各自添加一个 filter，两个条件都会生效。

### Step 5: 端点级访问拦截

在端点函数最顶部检查角色，直接 403 拦截：

```python
@followups_bp.route('/reminders', methods=['GET'])
def get_reminders():
    """获取服用周期提醒列表"""

    # 游客禁止访问
    if _has_role('guest'):
        return jsonify({"error": "游客无权访问"}), 403

    # ↓ 以下是正常逻辑
    session = db.session
    ...
```

同样的模式适用于所有需要角色拦截的端点：
- 获取列表的 GET 端点
- 修改数据的 POST/PUT/DELETE 端点

### Step 6: 清除缓存与重启

```bash
# 每次修改后端角色逻辑后：
find /path/to/api -name '__pycache__' -exec rm -rf {} + 2>/dev/null
fuser -k 8080/tcp 2>/dev/null
sleep 2
gunicorn -w 4 -b 127.0.0.1:8080 app:app
```

---

## Frontend Integration (Vanilla JS PWA)

### Store 中添加角色检测

```javascript
// store.js
const Store = {
  // ... 已有方法 ...

  isGuest() {
    const user = this.getUser();
    return user && (
      user.role === 'guest' ||
      (user.roles && user.roles.indexOf('guest') !== -1)
    );
  },

  hasRole(roleName) {
    const user = this.getUser();
    if (!user) return false;
    if (user.role === roleName) return true;
    return user.roles && user.roles.indexOf(roleName) !== -1;
  }
};
```

### Api 中添加入口

```javascript
// api.js
const Api = {
  // ...

  /* 游客登录 */
  async guestLogin() {
    const data = await this.post('/api/auth/guest-login', {});
    Store.setToken(data.token);
    Store.setUser({
      username: data.username,
      full_name: data.full_name,
      roles: data.roles || [data.role]
    });
    return data;
  },
};
```

### 路由守卫（Router Guard）

```javascript
// router.js
const Router = {
  init() {
    const onHash = () => {
      const hash = window.location.hash || '#/login';
      const name = hash.replace(/^#\/?/, '').split('/')[0] || 'login';

      // 未登录跳登录
      if (name !== 'login' && !Store.isLoggedIn()) {
        this.go('#/login');
        return;
      }
      // 已登录在登录页 → 跳默认页
      if (name === 'login' && Store.isLoggedIn()) {
        this.go('#/pickup');
        return;
      }
      // 游客只能访问特定页面
      if (Store.isGuest() && name !== 'pickup') {
        this.go('#/pickup');
        return;
      }

      // ... 正常路由分发
    };
  }
};
```

### UI 隐藏（导航标签/按钮）

**HTML 标记**：给需要根据角色隐藏的元素加上标记类
```html
<!-- 游客隐藏的导航标签 -->
<a href="#/followup" data-tab="followup" class="nav-guest-hidden">复诊</a>
<a href="#/reminders" data-tab="reminders" class="nav-guest-hidden">提醒</a>
```

**JS 控制显示/隐藏**：
```javascript
function updateHeader() {
  const user = Store.getUser();
  if (user) {
    // 游客隐藏特定导航
    document.querySelectorAll('.nav-guest-hidden').forEach(el => {
      el.style.display = Store.isGuest() ? 'none' : '';
    });
  }
}
```

**页面内元素隐藏**（如筛选标签）：
```javascript
// page-pickup.js
function render() {
  // 渲染 HTML（包含所有标签，用 guest-hidden 标记）
  container.innerHTML = `
    <span class="filter-tab guest-hidden" data-filter="全部">全部</span>
    <span class="filter-tab guest-hidden" data-filter="欠药">欠药</span>
    <span class="filter-tab active" data-filter="未取">未取</span>
  `;

  // 游客隐藏不需要的标签
  if (Store.isGuest()) {
    document.querySelectorAll('.guest-hidden').forEach(el => {
      el.style.display = 'none';
    });
  }
}
```

---

## Pitfalls

### 字段级 UI 控制（Detail Popup）

除了隐藏整个页面/tab，有时需要**在同一个弹窗/列表中根据角色隐藏特定字段**：

```javascript
// 1. 在 fields 数组中保留所有字段（不跳过）
var fields = [
  ['患者姓名', item.patient_name],
  ['患者电话', item.patient_phone],  // ← 正常显示
  ['快递地址', item.express_address],
];

// 2. 在渲染循环中按角色跳过敏感字段
var detailHtml = '';
for (var i = 0; i < fields.length; i++) {
  var val = fields[i][1];
  if (val === null || val === undefined || val === '') continue;

  // 游客隐藏电话号码
  if (Store.isGuest() && fields[i][0] === '患者电话') continue;

  detailHtml += '<div class="modal-detail-row">'
    + '<span class="label">' + escapeHtml(fields[i][0]) + '</span>'
    + '<span class="value">' + escapeHtml(String(val)) + '</span>'
    + '</div>';
}
```

**为什么不在 fields 数组中用三元移除？** 因为 `...(Store.isGuest() ? [] : [['患者电话', x]])` 的 spread 语法在部分老旧手机浏览器上不支持。而循环中 `continue` 写法兼容所有浏览器。

**可扩展的字段控制模式**：

```javascript
// 定义字段权限映射
var FIELD_ROLE_RULES = {
  '患者电话': ['admin', 'assistant'],   // 只有这些角色能看到
  '快递地址': ['admin'],                 // 更严格
};

for (var i = 0; i < fields.length; i++) {
  var val = fields[i][1];
  var label = fields[i][0];
  if (val === null || val === undefined || val === '') continue;

  // 检查字段权限
  var allowedRoles = FIELD_ROLE_RULES[label];
  if (allowedRoles) {
    var user = Store.getUser();
    var userRoles = user ? (user.roles || [user.role]) : [];
    var hasAccess = allowedRoles.some(function(r) {
      return userRoles.indexOf(r) !== -1;
    });
    if (!hasAccess) continue;
  }

  detailHtml += '...';
}
```

### ⚠️ 后端是唯一安全屏障

前端 UI 隐藏只是用户体验优化，**真正的权限检查必须在后端做**。攻击者可以直接 curl 调用 API，绕过前端限制。本例中后端所有相关端点都做了角色检查（返回 403）。

### ⚠️ Gunicorn Worker 缓存导致不一致

修改后端角色逻辑后，不同 worker 可能加载新旧不同的代码，导致测试结果时对时错。必须：
1. 清 `__pycache__`
2. `fuser -k <port>/tcp` 杀死所有 worker
3. 重新启动

### ⚠️ 角色叠加的过滤条件

当用户有多个角色（如 `guest` + `assistant`），SQLAlchemy 的 filter 会叠加（AND 逻辑）。需要确保叠加后的语义正确：
```python
# 两个 filter 叠加 = status='未取' AND (assistant IN [...])
query = query.filter(PrescriptionRecord.status == '未取')
query = _apply_assistant_filter(query, PrescriptionRecord)  # 添加 assistant 条件
```

如果不想叠加而是互斥（如 guest 角色忽略 assistant 过滤），需要用 `if/elif` 控制流：

```python
if _has_role('guest'):
    query = query.filter(PrescriptionRecord.status == '未取')
    # 不添加 assistant 过滤，guest 只看未取（不管是谁的）
elif _has_role('assistant'):
    query = _apply_assistant_filter(query, PrescriptionRecord)
```

### ⚠️ Login 页需要显式隐藏导航

登录页渲染时务必隐藏顶部栏和底部导航：
```javascript
document.getElementById('bottom-nav').style.display = 'none';
document.getElementById('app-header').style.display = 'none';
```
否则登录页会看到其他页面的 UI。

---

## Verification Checklist

- [ ] 游客登录端点 `POST /api/auth/guest-login` 返回 200 + token
- [ ] 游客只能看到预期数据（如只返回 status=未取的记录）
- [ ] 游客访问受限端点（复诊/提醒/更新）返回 403
- [ ] 正常用户登录后不受影响，仍可访问所有端点
- [ ] 游客前端看不到非授权的导航标签/按钮
- [ ] 游客手动输入受限路由 URL 会被路由守卫重定向
- [ ] 清除缓存重启后，旧 worker 不会返回错误结果
- [ ] 退出登录后 token 清除，重新进入 login 页

---

## References

- Flask-JWT-Extended: https://flask-jwt-extended.readthedocs.io/
- PyJWT: https://pyjwt.readthedocs.io/
- Role-Based Access Control (RBAC) pattern: https://en.wikipedia.org/wiki/Role-based_access_control

### Session References

- `references/guest-login-and-param-mismatch.md` — Full debug transcript, curl test commands, and file list for the guest login implementation and parameter mismatch fix.
