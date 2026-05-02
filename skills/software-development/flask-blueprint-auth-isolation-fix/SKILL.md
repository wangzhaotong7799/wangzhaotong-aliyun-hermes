---
name: flask-blueprint-auth-isolation-fix
description: "[已合并到 flask-blueprint-troubleshooting] 修复 Flask Blueprint 中装饰器作用域隔离问题，解决因重复模块导入导致的运行时错误"
version: 1.0.0
tags: [archived, flask, python, blueprint, authentication, gunicorn, debugging]
---

# Flask Blueprint 认证装饰器作用域隔离修复指南

## Overview

本技能解决在创建新 Flask Blueprint 时遇到的装饰器作用域问题，特别是当项目存在多个版本的同名模块（如 `/backend/auth.py` vs `/backend/api/v1/auth.py`）时。

**核心原则**: 即使函数本身使用正确的导入路径，如果装饰器来自旧模块，仍然会导致运行时错误

---

## When to Use

**适用场景:**
- 创建新的 Flask Blueprint 并使用 `@auth_required` 等装饰器
- 代码看起来正确但仍然报错 "ImportError: cannot import name"
- Gunicorn 崩溃日志指向旧的模块文件而不是你修改的文件
- traceback 显示 `File "/path/to/OLD_module.py", line X, in decorated_function`

**典型症状链:**
```
前端调用 /api/new-endpoint 
→ 后端返回 500 Internal Server Error  
→ 查看日志发现 ImportError  
→ 修复导入路径后问题依然存在
→ 检查 traceback 发现装饰器来自旧文件
```

---

## Problem Pattern

### 常见情况示例

项目结构中存在多个 auth.py：
```
/backend/auth.py                    ← 遗留代码
/backend/api/v1/auth.py             ← 新代码
/backend/gaofang-v2/auth.py         ← 可能也有备份
```

**错误的做法**（看似合理但会失败）：
```python
# api/v1/auth.py
from flask import Blueprint, request, jsonify, g
from database import get_db_session
from auth import auth_required  # ← Python 会找到 /backend/auth.py!

assistants_bp = Blueprint('assistants', __name__, url_prefix='/api')

@assistants_bp.route('/assistants', methods=['GET'])
@auth_required  # ← 这个装饰器在旧文件的上下文中执行
def get_assistants():
    from models import User, Role  # ← 这里虽然用了对的路径...
    
    with get_db_session() as db:
        users = db.query(User).filter(...).all()
        return jsonify([u.name for u in users]), 200
```

**为什么失败？**

虽然函数体中使用的是正确的 `from models import ...`，但 `@auth_required` 装饰器是从旧 `/backend/auth.py` 导入的。这个装饰器的 `decorated_function` 会在它自己定义的模块上下文中执行，导致隐式的模块依赖混乱。

---

## Step-by-Step Diagnosis

### 1. 检查是否存在重复模块文件

```bash
find . -name "auth.py" -type f
```

输出示例：
```
./backend/auth.py                    ← 遗留版本 (8KB)
./backend/api/v1/auth.py             ← 新版本 (14KB)
./backend/gaofang-v2/auth.py         ← 备份？
```

### 2. 验证装饰器的实际来源

在应用启动后或 Python REPL 中：
```python
import inspect
from auth import auth_required
print(inspect.getfile(auth_required))
# 输出应该是你期望的文件路径，如果不是 → 有问题！
```

### 3. 仔细检查错误日志

关键线索：错误 traceback 中的文件路径
```
File "/root/projects/gaofang-v2/backend/auth.py", line 92, in decorated_function
    return f(*args, **kwargs)
File "/root/projects/gaofang-v2/backend/api/v1/auth.py", line 137, in get_assistants
    from database import User, Role   # ← 这是你的代码，但已经晚了！
ImportError: cannot import name 'User'
```

注意第一个文件是 `/backend/auth.py` 而不是 `/backend/api/v1/auth.py`

### 4. 检查 sys.path 优先级

```python
import sys
print(sys.path[:5])
```

如果 `.` 或当前目录在前面，Python 会优先加载顶层的同名模块。

---

## Solution: Self-Contained Decorator

将装饰器的完整定义复制到新的蓝图文件中，确保完全独立：

### 完整修复方案

**修改目标文件：** `/backend/api/v1/auth.py`

**步骤 1:** 在文件开头添加自包含的装饰器定义

```python
# -*- coding: utf-8 -*-
"""
Authentication Blueprint - V1 Compatible API
"""
from flask import Blueprint, request, jsonify, g
from functools import wraps
from sqlalchemy.orm import Session
from database import get_db_session
import jwt
from datetime import datetime, timedelta
from pytz import utc

# JWT Configuration - replace with your actual secret
JWT_SECRET = os.environ.get('JWT_SECRET_KEY', 'default-secret-key')
JWT_ALGORITHM = 'HS256'


def verify_token(token: str):
    """Verify and decode JWT token"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def auth_required(f):
    """Decorator to require authentication - SELF-CONTAINED VERSION"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = None
        
        # Get token from Authorization header
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
        
        if not token:
            return jsonify({"error": "Missing authorization token"}), 401
        
        payload = verify_token(token)
        if not payload:
            return jsonify({"error": "Invalid or expired token"}), 401
        
        # Store user info in Flask's g object
        g.user_id = payload['user_id']
        g.username = payload['username']
        g.roles = payload.get('roles', [])
        
        return f(*args, **kwargs)
    
    return decorated_function


# Now you can still import other utilities from old module
from auth import (
    register_user, login_user, get_user_info, update_user, 
    change_password, permission_required  # ← 移除 auth_required
)
```

**步骤 2:** 使用本地定义的装饰器

```python
assistants_bp = Blueprint('assistants', __name__, url_prefix='/api')

@assistants_bp.route('/assistants', methods=['GET'])
@auth_required  # ← 现在使用的是当前文件中定义的版本！
def get_assistants():
    from models import User, Role
    
    with get_db_session() as db:
        query = db.query(User).join(User.roles).filter(
            Role.name == 'assistant',
            User.status == 'active'
        )
        
        users = query.all()
        assistants = sorted(set([u.full_name or u.username for u in users]))
        
        return jsonify(assistants), 200
```

---

## Critical Cleanup Steps

**必须彻底清理 Python 字节码缓存！**

Gunicorn 工人进程会保留编译后的 `.pyc` 文件。如果不强制清理：
- 旧字节码继续被加载
- 你的代码修改不会生效
- 错误日志依然指向旧文件

### 强制重启流程

```bash
# 1. 杀死所有 Gunicorn 进程
pkill -9 gunicorn
sleep 2

# 2. 进入后端目录
cd /path/to/backend

# 3. 删除所有 Python 缓存
find . -name "*.pyc" -delete
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null

# 4. 重新启动（推荐开启 --reload 模式）
gunicorn --bind 127.0.0.1:5000 --workers 4 --reload app:app
```

**验证成功标志：**
```
[INFO] Listening at: http://127.0.0.1:5000
[INFO] Booting worker with pid: XXXXX (4 workers)
```

---

## Verification

### 测试端点

```python
import urllib.request
import json

# Login
login_data = json.dumps({"username": "admin", "password": "password"}).encode()
req = urllib.request.Request(
    'http://localhost:5000/api/auth/login',
    data=login_data,
    headers={'Content-Type': 'application/json'}
)
with urllib.request.urlopen(req) as resp:
    token = json.loads(resp.read())['token']

# Test new endpoint
req2 = urllib.request.Request(
    'http://localhost:5000/api/assistants',
    headers={'Authorization': f'Bearer {token}'}
)
with urllib.request.urlopen(req2) as resp:
    data = json.loads(resp.read().decode())
    print(f"Success! Got {len(data)} items")
```

### 检查错误日志

```bash
# 应该没有 traceback 了
tail -50 /var/log/gunicorn_error.log | grep -E "(Traceback|ERROR)"
```

---

## Common Pitfalls

### ❌ Don'ts

1. **不要只修复导入语句**  
   装饰器的定义文件才是问题的根源

2. **不要假设 Gunicorn 自动重载**  
   除非明确配置了 `--reload`，否则需要手动重启

3. **不要忘记清除 `.pyc` 缓存**  
   不删缓存等于白改代码

4. **不要忽略 traceback 的文件路径**  
   它告诉你实际执行的代码在哪里

### ✅ Dos

1. **让新蓝图完全独立**  
   复制所有需要的辅助函数和装饰器

2. **强制终止所有 Gunicorn 进程**  
   `pkill -9` 确保无残留

3. **验证错误日志不再指向旧文件**  
   修改后要确认 traceback 中的路径正确

4. **同时修复前端调用**  
   确保前端传递正确的 Authorization header

---

## Related Scenarios

### 前端忘记传递 Token

**症状：** HTTP 401 UNAUTHORIZED

**检查：**
```javascript
// Wrong - no token
fetch('/api/assistants')

// Correct - with token
fetch('/api/assistants', {
    headers: {
        'Authorization': 'Bearer ' + localStorage.getItem('token')
    }
})
```

### SQLAlchemy 模型导入路径

**症状：** `ImportError: cannot import name 'User'`

**检查项目结构：**
```bash
# 找到实际位置
find . -name "user.py" | grep model

# 通常是 /models/user.py 而非 /database.py
```

**正确使用：**
```python
# Old style
from database import User, Role

# New style  
from models import User, Role, PrescriptionRecord
```

---

## Quick Reference Card

```python
# Correct self-contained decorator pattern

from functools import wraps
from flask import request, jsonify, g
import jwt

def auth_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # ... auth logic here
        return f(*args, **kwargs)
    return decorated_function

blueprint = Blueprint('name', __name__, url_prefix='/api')

@blueprint.route('/endpoint')
@auth_required  # Uses local definition
def handler():
    # Your code here
    pass
```

```bash
# Force restart Gunicorn

pkill -9 gunicorn
find . -name "*.pyc" -delete
find . -type d -name "__pycache__" -exec rm -rf {} +
gunicorn --bind 127.0.0.1:5000 --workers 4 --reload app:app
```

---

## Troubleshooting Checklist

- [ ] 使用 `find . -name "auth.py"` 查找所有同名模块
- [ ] 检查 traceback 中的文件路径是否是你修改的文件
- [ ] 在新蓝图文件中定义自包含的装饰器
- [ ] 从旧模块导入列表中移除已自包含的装饰器
- [ ] 执行 `pkill -9 gunicorn` 强制停止
- [ ] 删除所有 `*.pyc` 和 `__pycache__` 目录
- [ ] 重新启动 Gunicorn
- [ ] 测试 API 端点
- [ ] 检查错误日志确认无 traceback
- [ ] 验证前端正确传递 Authorization header

---

## References

- Flask Blueprints: https://flask.palletsprojects.com/en/latest/blueprints/
- Python Import System: https://docs.python.org/3/reference/import.html
- Gunicorn Workers: https://docs.gunicorn.org/en/stable/design.html

---

## Real-World Example: 膏方管理系统 V2

**问题背景：**
- 系统有 `/backend/auth.py` (旧版，8KB) 和 `/backend/api/v1/auth.py` (新版，14KB)
- 前端调用的 `/api/assistants` 接口不存在，需要新建

**错误现象：**
```
✗ /api/assistants returns 500
✗ Logs show: File "/backend/auth.py", line 92, in decorated_function
✗ Fixing import path doesn't help
```

**解决步骤：**
1. 在新文件中添加 `verify_token()` 和 `auth_required()` 完整定义
2. 移除对旧模块中 `auth_required` 的导入
3. 清理 `*.pyc` 缓存
4. 重启 Gunicorn
5. 前端添加 Authorization header

**结果：** ✅ API 正常返回医助列表数据

---

## Author Notes

此技能基于实际调试经历总结，涉及 Flask 应用的深层机制理解。装饰器的作用域问题在 Flask Blueprint 开发中非常隐蔽且容易被忽视，建议遇到类似问题时首先怀疑这一点。