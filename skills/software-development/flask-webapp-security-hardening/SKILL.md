---
name: flask-webapp-security-hardening
description: "Flask Web 应用安全加固 + JWT 角色权限管理 — 评估、加固、访问控制、前端集成"
version: 1.1.0
author: Hermes Agent
tags: [flask, security, hardening, modernization, python, jwt, role, access-control, auth]
toolsets_required: ['terminal', 'file']
category: software-development
metadata:
  hermes:
    tags: [flask, security, hardening, modernization, python, jwt, role, access-control, auth]
  applicability: production-flask-apps
  priority: high
  estimated_effort: 1-2 weeks
---

# 🔐 Flask Web 应用安全加固与现代化改造 v1.0

## 🎯 适用场景

当您的 Flask 应用出现以下情况时，应考虑进行安全加固：

- Python 版本较旧 (如 3.6.x EOL)
- 直接使用 SQLite 作为生产数据库
- 所有路由集中在单个 app.py 文件中
- 使用 HTTP 而非 HTTPS
- 缺乏 API 限流和安全中间件
- 未实现自动化测试

---

## ⚠️ 第一阶段：快速诊断 (30 分钟)

### 1. 项目规模评估
```bash
# 统计代码量
find ~/projects/app -name '*.py' | wc -l           # Python 文件数
find ~/projects/app -name '*.py' -exec cat {} + | wc -l  # 代码行数
grep -h '@app.route' app.py | wc -l               # API 路由数
```

### 2. 依赖项安全检查
```bash
pip list --outdated                                # 过时包
pip install safety                                 # 安全扫描工具
safety check                                       # 漏洞检测
```

### 3. 潜在安全风险扫描
```bash
# 检测未参数化的 SQL 查询
grep -v "cursor.execute.*?" app.py | grep -i execute

# 检测硬编码密码/密钥
grep -rE "(password|secret|api_key)\s*=\s*['\"][^'\"]+['\"]" .

# 检测调试模式是否开启
grep "debug=True" app.py
```

---

## 🔧 第二阶段：核心安全加固 (优先级最高)

### 1. JWT Token Bytes/String兼容性问题

#### 症状
登录返回的 token 格式异常：
```json
// 错误的格式
{"token": "b'eyJ0eX..."}  // ❌ 被当作字符串字面量

// 正确的格式  
{"token": "eyJ0eX..."}    // ✅ 纯字符串
```

#### 根本原因
PyJWT 新版本默认返回 bytes 类型，而旧版本返回 str

#### 解决方案
在 auth.py 中修改 generate_token 函数：

```python
def generate_token(user_id, username, roles):
    """生成 JWT 令牌"""
    payload = {
        'user_id': user_id,
        'username': username,
        'roles': roles,
        'exp': datetime.utcnow() + timedelta(seconds=JWT_EXPIRATION)
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    
    # 关键修复：确保返回字符串而不是 bytes
    if isinstance(token, bytes):
        token = token.decode('utf-8')
    return str(token)  # 最终确保是 str 类型
```

**注意**：不要在 app.py 中重复对 token 调用 str()，这会产生 `'b\\'...\\''` 这种错误格式。

---

### 1b. JWT 角色权限管理（RBAC）

> **吸收自 `flask-jwt-role-access`**

当需要不同用户看到不同数据（行级权限）、某些端点只对特定角色开放、或添加受限角色（如只读游客）时，使用 RBAC 模式。

#### 后端实现

**Step 1 — JWT Token 中加入角色字段：**
```python
def generate_token(user_id, username, roles):
    payload = {
        'user_id': user_id, 'username': username,
        'roles': roles,  # 如 ['guest'] 或 ['assistant', 'admin']
        'exp': datetime.utcnow() + timedelta(hours=24)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm='HS256')
```

**Step 2 — 角色检测辅助函数：**
```python
def _has_role(role_name):
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    payload = verify_token(token)
    if payload and role_name in payload.get('roles', []):
        return True
    return False
```

**Step 3 — 基于角色的数据过滤（行级权限）：**
```python
query = session.query(PrescriptionRecord)
if _has_role('guest'):
    query = query.filter(PrescriptionRecord.status == '未取')
```

**Step 4 — 端点级访问拦截：**
```python
if _has_role('guest'):
    return jsonify({"error": "游客无权访问"}), 403
```

#### 关键陷阱

- **Gunicorn 缓存不一致**：修改角色逻辑后必须清 __pycache__ 并 `fuser -k <port>/tcp` 重启
- **角色叠加**：SQLAlchemy filter 默认 AND 叠加，需要互斥时用 `if/elif` 控制流
- **搜索参数不应按角色封锁**：搜索/筛选权限与数据查看权限是两码事
- **⚠️ 重构时装饰器丢失（本次踩坑）**：把"手动解析 token"（`verify_token(request.headers)`）重构为统一权限函数（`get_visible_scope()` 依赖 `@auth_required` 注入的 `g.user_id`）时，必须同步给**所有路由补 `@auth_required`**。否则 `g.user_id` 从不注入 → 数据范围过滤/字段脱敏全部失效 + **匿名可访问写接口（安全漏洞）**。重构后用匿名请求测试 `GET/POST/DELETE` 应返回 401 来验证。
- **数据范围解析优先级**：super_admin > pharmacy_admin > leadership > director（查 director_group_scope 表）> group_leader（本组）> assistant（自己），返回 None=全部可见，纯数据库查询无硬编码账号
- **字段级权限**：敏感字段（剂型/医生）用 `xxx:view` 权限点控制，后端返回时置 None + 前端按 `/me` permissions 动态隐藏列，双保险

#### 引用文件

| File | Content |
|------|---------|
| `references/flask-jwt-frontend-integration.md` | 完整前端集成（路由守卫、UI隐藏、字段级控制、guest login API） |
| `references/user-role-permission-debug.md` | 角色/权限表为空导致 403 的排查 |

---

### 2. 修复 SQL 注入漏洞

#### 错误示例
```python
# ❌ 不安全
query = f"SELECT * FROM users WHERE id = {user_id}"
cursor.execute(query)

# ❌ 同样危险
query = f"SELECT * FROM users WHERE name = '{username}'"
cursor.execute(query)
```

#### 正确做法
```python
# ✅ 参数化查询
cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))

# ✅ 多参数
cursor.execute(
    "SELECT * FROM users WHERE status = ? AND role_id = ?",
    (status, role_id)
)
```

#### 批量修复脚本
```bash
# 查找所有需要修复的地方
grep -n "execute.*f\"" app.py | head -50

# 逐条检查并手动修改
```

---

### 3. 部署 HTTPS (Let's Encrypt)

```bash
# 安装 Certbot
sudo yum install certbot python3-certbot-nginx

# 获取证书
sudo certbot --nginx -d yourdomain.com

# 自动续期
sudo systemctl enable certbot.timer
```

---

### 4. 添加 WSGI 服务器 (Gunicorn)

```python
# 停止使用 app.run()，改用 gunicorn
# ❌ 不要在生产环境使用
app.run(debug=True, host='0.0.0.0', port=8080)

# ✅ 改为 Gunicorn
gunicorn -w 4 -b 0.0.0.0:8080 app:app
```

配置 systemd 服务：
```ini
# /etc/systemd/system/gaofang.service
[Unit]
Description=GaoFang Flask App
After=network.target

[Service]
Type=idle
User=www-data
WorkingDirectory=/root/projects/gaofang
Environment="PATH=/root/.local/bin"
ExecStart=/usr/bin/gunicorn -w 4 -b 0.0.0.0:8080 app:app

[Install]
WantedBy=multi-user.target
```

---

### 5. 添加 API 限流中间件

```python
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    app,
    key_func=get_remote_address,
    default_limits=["100 per minute"]
)

@app.route('/api/critical', methods=['POST'])
@limiter.limit("10 per minute")
def critical_operation():
    pass
```

---

### 6. CSRF/XSS防护

#### Flask-Talisman (HTTP 安全头)
```bash
pip install flask-talisman
```

```python
from flask_talisman import Talisman

csp = {
    'default-src': "'self'",
    'script-src': ["'self'", "https://cdn.jsdelivr.net"],
}

Talisman(app,
    force_https=True,
    content_security_policy=csp,
    session_cookie_http_only=True)
```

#### XSS 转义
```python
from markupsafe import escape

# ✅ 永远转义用户输入
html = f"<div>{escape(user_input)}</div>"
```

---

## 🏗️ 第三阶段：架构重构

### 1. Flask Blueprint 模块化

```python
# apps/blueprints/auth.py
from flask import Blueprint

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

@auth_bp.route('/login', methods=['POST'])
def login():
    pass

# app.py
from apps.blueprints.auth import auth_bp

app.register_blueprint(auth_bp)
```

### 2. 引入 SQLAlchemy ORM（可选）

```python
# 配置
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///gaofang.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

# 模型定义
class User(db.Model):
    id = db.Column(Integer, primary_key=True)
    username = db.Column(String(50), unique=True)
    password_hash = db.Column(String(255))
```

---

## 🧪 第四阶段：质量保证

### 1. 单元测试框架 (pytest)

```bash
pip install pytest pytest-cov
```

```python
# tests/test_auth.py
import pytest
from api import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_login_success(client):
    response = client.post('/api/auth/login', json={
        'username': 'admin',
        'password': 'admin123'
    })
    assert response.status_code == 200
    data = response.get_json()
    assert 'token' in data
```

运行测试：
```bash
pytest --cov=. --cov-report=html
```

---

## 📋 安全检查清单

在每次上线前核对：

```markdown
## 🔒 安全加固检查清单

### 基础安全
- [ ] Python 版本 >= 3.8
- [ ] debug=False
- [ ] JWT SECRET 长度 > 32 字符
- [ ] 密码使用 bcrypt/sha256 加密
- [ ] HTTPS 已启用
- [ ] SSL 证书自动续期配置

### 访问控制
- [ ] 所有 API 需要认证
- [ ] 敏感接口增加角色验证
- [ ] JWT token 设置合理过期时间

### 输入验证
- [ ] 所有 SQL 使用参数化查询
- [ ] 用户输入长度限制
- [ ] SQL 注入测试通过
- [ ] XSS 攻击测试通过

### 性能与稳定
- [ ] 使用 Gunicorn/uWSGI
- [ ] 配置合适的 worker 数量
- [ ] 添加 API 限流
- [ ] 错误页面不泄露敏感信息

### 备份与恢复
- [ ] 定时备份配置完成
- [ ] 备份恢复流程已测试
- [ ] 最近一次恢复演练成功
```

---

## 🚨 常见陷阱与解决方案

| 问题 | 现象 | 解决方案 |
|------|------|---------|
| JWT token 认证失败 | 返回 `"b'eyJ...'"` 格式 | 在 auth.py 统一处理 bytes→str |
| SQL 执行报错 | TypeError: sequence item | 全部改为参数化查询 |
| 静态资源加载慢 | CDN 未启用 | Bootstrap 等使用 CDN |
| 重启后服务失效 | systemd 未配置 | 创建 .service 文件 |
| 端口冲突 | Address already in use | 检查 netstat 并释放端口 |

---

## 📊 预期效果对比

| 指标 | 加固前 | 加固后 |
|------|--------|--------|
| Python 版本 | 3.6 (EOL) | 3.9+ |
| SQL 安全 | 部分参数化 | 100% 参数化 |
| 传输协议 | HTTP | HTTPS |
| 并发能力 | ~100 req/min | ~5000 req/min |
| 测试覆盖率 | 0% | >60% |

---

## 🔗 相关资源

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [Flask Security Best Practices](https://flask.palletsprojects.com/en/latest/security/)
- [Python Security Checklist](https://checklist.pythonsecurity.io/)

---

*创建时间*: 2026-04-23  
*最后更新*: 2026-04-23  
*作者*: Hermes Agent  
*适用项目*: Flask Web 应用安全加固

---

## Absorbed Skills

The following former standalone skills have been consolidated into this umbrella.
Their content is preserved as reference files:

| Former Skill | Reference File | Content Summary |
|:---|---|:---|
| `flask-jwt-role-access` | `references/flask-jwt-frontend-integration.md` | JWT roles in token, guest login endpoint, frontend Store/Api/router integration, UI field-level visibility per role |
| `flask-user-role-permission-debug` | `references/user-role-permission-debug.md` | Empty permissions table diagnosis, debug queries for missing role-permission mappings |
