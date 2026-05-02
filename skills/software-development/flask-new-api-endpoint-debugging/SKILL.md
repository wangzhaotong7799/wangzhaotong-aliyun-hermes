---
name: flask-new-api-endpoint-debugging
description: "[已合并到 flask-blueprint-troubleshooting] 在 Flask 应用中创建和调试新 API 端点的系统方法，处理导入错误、认证问题和模块冲突"
version: 1.0.0
tags: [archived, flask, api, debugging, authentication, import-errors]
---

# Flask 新 API 接口调试与常见问题排查

## Overview

本技能提供在现有 Flask 应用中添加新 API 端点时的系统化调试方法，涵盖从路由注册、模块导入到认证配置的完整工作流。

**核心经验**: 500 错误的根本原因往往不在新代码本身，而在环境配置（旧文件干扰、缓存、导入路径不一致）。

---

## When to Use

**适用场景:**
- 创建了新的 API Blueprint 但调用时返回 HTTP 500
- `ImportError: cannot import name 'X' from module` 
- 认证成功但在函数执行时报错"无效令牌"
- 修改代码后错误依旧（可能 Python 缓存未清除）
- Gunicorn 日志指向不存在的文件路径

---

## Common Issues and Solutions

### Issue 1: 重复模块文件导致的路径冲突

**现象**: Gunicorn 报错指向 `/backend/auth.py` 而非预期的 `/backend/api/v1/auth.py`

**检查命令**:
```bash
find /path/to/project/backend -name "auth.py" -type f
```

**预期输出** (应该只有 1 个):
```
/path/to/project/backend/api/v1/auth.py
```

**问题输出** (有 2 个文件):
```
/path/to/project/backend/auth.py         # ❌ 旧文件
/path/to/project/backend/api/v1/auth.py  # ✅ 正确位置
```

**解决方案**:

1. **查找并修复所有引用**:
```python
# ❌ 错误引用 (指向根目录)
from auth import verify_token
from auth import generate_token

# ✅ 正确引用
from api.v1.auth import verify_token
from api.v1.auth import generate_token
```

2. **删除或重命名旧文件**:
```bash
mv /root/projects/gaofang-v2/backend/auth.py \
   /root/projects/gaofang-v2/backend/auth.py.bak
```

3. **验证 import 是否成功**:
```python
python3 -c "from api.v1.auth import assistants_bp; print('OK')"
```

### Issue 2: SQLAlchemy 模型导入路径错误

**现象**: 
```
ImportError: cannot import name 'User' from database
```

**根本原因**: 项目使用 `models/` 包组织 ORM 模型，而新代码尝试从旧的 `database.py` 导入

**检查方法**:
```bash
# 查看项目结构
ls backend/database*.py backend/models/*.py 2>/dev/null

# 确认 models/__init__.py 导出了哪些类
cat backend/models/__init__.py
```

**典型输出**:
```python
# models/__init__.py
from .base import Base
from .user import User
from .role import Role, Permission
from .prescription import PrescriptionRecord
from .log import StatusChangeLog

__all__ = ['Base', 'User', 'Role', 'Permission', 
           'PrescriptionRecord', 'StatusChangeLog']
```

**错误示例**:
```python
@new_bp.route('/data')
def get_data():
    from database import User  # ❌ 会失败！
    users = db.query(User).all()
    return jsonify([u.name for u in users])
```

**正确做法**:
```python
@new_bp.route('/data')
def get_data():
    from models import User  # ✅ 正确
    users = db.query(User).all()
    return jsonify([u.name for u in users])
```

**批量修复**:
```bash
cd /root/projects/gaofang-v2/backend
find api/v1 -name "*.py" -exec grep -l "from database import.*User" {} \;
# 对找到的文件逐个修复
```

### Issue 3: Python 缓存 `.pyc` 导致旧代码生效

**现象**: 已修复代码并重启 Gunicorn，但错误日志仍显示旧的 traceback

**关键识别特征**:
- 错误指向已经删除的行号
- 修复的语法错误仍然报同样的错
- `pgrep gunicorn` 显示进程已启动很久（几分钟以上）

**彻底清理步骤**:
```bash
# 1. 停止 Gunicorn
pkill -9 gunicorn

# 2. 等待进程完全退出
sleep 3

# 3. 强制删除所有 Python 缓存
cd /root/projects/gaofang-v2/backend

# 删除所有 .pyc 文件
find . -name "*.pyc" -delete 2>/dev/null

# 删除所有 __pycache__ 目录
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null

# 4. 验证清理结果
find . -name "*.pyc" -o -type d -name "__pycache__"
# 应该无输出

# 5. 重新启动
/usr/local/bin/gunicorn --bind 127.0.0.1:5000 --workers 4 app:app &
```

**注意**: 某些 IDE 也会生成 `.pyc`，确保它们也不会再生成缓存：
```bash
# PyCharm/VSCode 等项目文件夹中可能也有缓存
rm -rf ~/.cache/Pycache/
```

### Issue 4: JWT Secret 不一致导致认证失败

**现象**: 函数内部收到 `{error: "无效或过期的令牌"}`

**调试脚本**:
```python
import sys
sys.path.insert(0, '/root/projects/gaofang-v2/backend')

from auth import JWT_SECRET, generate_token, verify_token

print(f"JWT_SECRET: {repr(JWT_SECRET)}")

# 测试生成和验证
token = generate_token(user_id=1, username="test", roles=["admin"])
decoded = verify_token(token)
print(f"验证结果：{decoded}")
```

**如果失败**,检查是否有多个 secret 定义:
```bash
grep -rn "JWT_SECRET\|SECRET_KEY" /root/projects/gaofang-v2/backend/ | head -20
```

**解决方案**:
- 统一使用同一模块中的 token 工具函数
- 确保 `app.py` 中的 `SECRET_KEY` 与 `auth.py` 中的 `JWT_SECRET` 一致

### Issue 5: Blueprint URL Prefix 导致的路径变化

**现象**: 期望访问 `/api/assistants` 但实际注册为 `/api/auth/assistants`

**检查注册的蓝图路径**:
```python
python3 -c "
import sys
sys.path.insert(0, '/root/projects/gaofang-v2/backend')
from app import app

for rule in app.url_map.iter_rules():
    if 'assistants' in str(rule):
        print(f'{rule:40s} -> {rule.endpoint}')
"
```

**解决方案**: 调整 Blueprint 的 url_prefix
```python
# ❌ 错误 - 注册在 /api/auth 下
auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

@auth_bp.route('/assistants')  # 实际路径：/api/auth/assistants
def get_assistants(): ...

# ✅ 正确 - 单独创建蓝图
assistants_bp = Blueprint('assistants', __name__, url_prefix='/api')

@assistants_bp.route('/assistants')  # 实际路径：/api/assistants
def get_assistants(): ...
```

---

## New Endpoint Development Workflow

### Step 1: Create the Blueprint Function

```python
# backend/api/v1/auth.py

from flask import Blueprint, request, jsonify
from functools import wraps

# 创建新蓝图
assistants_bp = Blueprint('assistants', __name__, url_prefix='/api')

def auth_required(f):
    """装饰器确保请求已认证"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # ... auth logic ...
        return f(*args, **kwargs)
    return decorated_function

@assistants_bp.route('/assistants', methods=['GET'])
@auth_required
def get_assistants():
    """获取医助列表
    
    Returns: List[str] - 医助姓名数组
    """
    from models import User, Role  # ⚠️ 关键：使用正确的导入
    
    with get_db_session() as db:
        query = db.query(User).join(User.roles).filter(
            Role.name == 'assistant',
            User.status == 'active'
        )
        
        users = query.all()
        names = sorted(set([u.full_name or u.username for u in users]))
        
        return jsonify(names), 200
```

### Step 2: Register in app.py

```python
# backend/app.py

# 导入新蓝图
from api.v1.auth import auth_bp, users_mgmt_bp, assistants_bp  # 添加 assistants_bp

# 注册蓝图
app.register_blueprint(auth_bp)           # /api/auth/*
app.register_blueprint(users_mgmt_bp)     # /api/users/*  
app.register_blueprint(assistants_bp)     # /api/assistants/* ← 新增
```

### Step 3: Clear Cache and Restart

```bash
cd /root/projects/gaofang-v2/backend

# 停止服务
pkill -9 gunicorn
sleep 2

# 清除缓存
find . -name "*.pyc" -delete
find . -type d -name "__pycache__" -exec rm -rf {} +

# 启动服务
/usr/local/bin/gunicorn --bind 127.0.0.1:5000 --workers 4 app:app &

# 验证进程启动
ps aux | grep '[g]unicorn' | wc -l
# 应该显示 5 (1 master + 4 workers)
```

### Step 4: Test the Endpoint

```python
import urllib.request
import json

# 获取 token
login_data = json.dumps({"username": "yizhu001", "password": "123456"}).encode()
req = urllib.request.Request(
    'http://127.0.0.1:5000/api/auth/login',
    data=login_data,
    headers={'Content-Type': 'application/json'}
)
with urllib.request.urlopen(req) as resp:
    token = json.loads(resp.read())['token']

# 测试新端点
req = urllib.request.Request(
    'http://127.0.0.1:5000/api/assistants',
    headers={'Authorization': f'Bearer {token}'}
)
with urllib.request.urlopen(req) as resp:
    data = json.loads(resp.read().decode())
    print(f"Success! Got {len(data)} assistants")
    for name in data[:5]:
        print(f"  - {name}")
```

---

## Debugging Tools

### Check Registered Routes
```bash
cd /root/projects/gaofang-v2/backend
python3 << 'EOF'
from app import app
for rule in sorted(app.url_map.iter_rules(), key=str):
    if '/api/' in str(rule) and not str(rule).startswith('/static'):
        print(f"{str(rule):45s} -> {rule.endpoint}")
EOF
```

### Local Function Test
```bash
python3 << 'PYTEST'
from flask import Flask
from database import db
from api.v1.auth import your_new_function
from auth import generate_token

app = Flask(__name__)
db.init_app(app)
token = generate_token(1, "test", ["admin"])

with app.app_context():
    with app.test_request_context(headers={"Authorization": f"Bearer {token}"}):
        try:
            result = your_new_function()
            content = result[0].get_json()
            print("Result:", content)
        except Exception as e:
            import traceback
            traceback.print_exc()
PYTEST
```

---

## Troubleshooting Decision Tree

```
500 Internal Server Error?
├─ 查看错误日志 traceback
│   ├─ ImportError → 检查模块导入路径 (database vs models)
│   ├─ NameError → 检查变量名/拼写/作用域  
│   ├─ TypeError → 检查参数类型/函数签名
│   └─ 其他异常 → 按具体错误修复
│
Authentication Failed ("无效令牌")?
├─ 检查 JWT_SECRET 是否一致
│   ├─ 不一致 → 统一使用 auth.generate_token()
│   └─ 一致 → 检查 token payload 内容
│
修改后错误依旧？
├─ 确认 Gunicorn 已真正重启 (pgrep -la gunicorn)
│   ├─ 进程还在运行 → pkill -9 强制停止
│   └─ 已重启 → 检查 .pyc 缓存
│
URL 404 Not Found?
├─ 检查前端调用的 URL vs 后端注册的 URL
│   ├─ 不匹配 → 调整 Blueprint url_prefix 或创建别名
│   └─ 匹配 → 确认 Blueprint 已正确注册到 app
```

---

## Important Notes

1. **导入一致性**: 整个项目中要么都用 `from models import X`, 要么都用 `from database import X`，不要混用
2. **Blueprint 名称唯一性**: 同一文件中每个 Blueprint 必须有不同名称（即使 url_prefix 相同）
3. **装饰器顺序**: 认证装饰器 (`@auth_required`) 应在路由装饰器之后
4. **缓存清理时机**: 每次修改 Python 代码后都建议清理 `.pyc`
5. **权限控制**: 新端点也需要适当的角色权限检查

---

## Quick Checklist

Before reporting a bug, verify:

- [ ] 新函数的导入语句使用正确的模块路径 (`from models import...`)
- [ ] Blueprint 已在 `app.py` 中通过 `register_blueprint()` 注册
- [ ] 没有同名的旧 Python 文件在别处存在
- [ ] Gunicorn 已完全重启 (`pgrep -c gunicorn` ≥ 3)
- [ ] Python 缓存已清除 (`find . -name "*.pyc"` 返回空)
- [ ] 测试时使用的是有效的 JWT token
- [ ] 查看错误日志的完整 traceback 而非只看最后一行

---

## References

- This skill was developed from real-world debugging of a multi-agent Flask application
- Related issues documented in production deployments of legacy system upgrades
- See also: flask-api-troubleshooting, flask-blueprint-api-debugging