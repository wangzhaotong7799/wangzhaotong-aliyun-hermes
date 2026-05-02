---
name: flask-postgresql-system-upgrade
title: Flask+SQLite 升级到 Flask+PostgreSQL 完整工作流
description: 单体应用现代化改造，保持功能零丢失的数据库迁移和架构重构指南
category: software-development
tags: [flask, postgresql, sqlite, sqlalchemy, migration]
---

## 适用场景
- 遗留系统现代化改造 (SQLite → PostgreSQL)
- 单体应用重构为模块化架构
- 保持业务功能零丢失的技术升级

## 核心原则
1. **功能一致性优先**: 升级前后 API 接口必须 100% 兼容
2. **目录隔离**: 新版本代码在新目录构建，不修改原项目
3. **端口分离**: 新旧版本并存以便测试对比
4. **断点续传**: 每个阶段生成检查点和日志，支持会话中断恢复

## 技术栈兼容性要求
| 组件 | 推荐版本 | Python 版本限制 |
|------|----------|----------------|
| Flask | 2.0.3 | 需 Python 3.6+ |
| SQLAlchemy | 1.4.46 | 需 Python 3.6+ |
| Flask-SQLAlchemy | 2.5.1 | 需 Python 3.6+ |
| psycopg2-binary | 2.9.3 | 无限制 |

## 典型升级流程

### 阶段 1: 环境准备
```bash
# CentOS/AlmaLinux 安装 PostgreSQL
sudo yum install postgresql postgresql-server
sudo postgresql-setup --initdb
sudo systemctl start postgresql

# 创建数据库和用户
sudo -u postgres psql << EOF
CREATE DATABASE app_v2;
CREATE USER app_user WITH PASSWORD 'secure-password';
GRANT ALL PRIVILEGES ON DATABASE app_v2 TO app_user;
EOF
```

### 阶段 2: 数据迁移 ⚠️关键点

#### 问题 1: SQLite vs PostgreSQL ID 冲突
**现象**: `foreign key constraint violated`

**原因**: SQLite AUTOINCREMENT 和 PostgreSQL SERIAL 行为不同

**❌ 错误做法**: 保留旧 ID
```python
conn.execute(User.__table__.insert().values(id=row['id'], ...))
```

**✅ 正确策略**: 不保留旧 ID，建立映射表
```python
user_id_map = {}  # old_id -> new_id

for row in user_rows:
    result = conn.execute(User.__table__.insert().values(
        username=row[1],  # 跳过 id
        email=row[2],
    ))
    new_id = list(result.inserted_primary_key)[0]
    user_id_map[row[0]] = new_id

# 关联表使用新 ID
conn.execute(user_roles.insert().values(
    user_id=user_id_map[old_user_id],
    role_id=role_id_map[old_role_id]
))
```

#### 问题 2: SQLAlchemy 1.4 API 差异
**现象**: `KeyError: 0` 或 `IndexError`

**解决**:
```python
# ✅ SQLAlchemy 1.4 写法
new_id = list(result.inserted_primary_key)[0]
```

#### 问题 3: Model 更新不生效
**解决**: Drop & Recreate 所有表
```python
Base.metadata.drop_all(engine)
Base.metadata.create_all(engine)
```

### 阶段 3: Blueprint 重构

#### 认证装饰器模板
```python
from functools import wraps
from flask import request, g, jsonify
import jwt

def auth_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        if not token:
            return jsonify({"error": "未认证"}), 401
        
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
            g.user_id = payload['user_id']
            g.roles = payload.get('roles', [])
            return f(*args, **kwargs)
        except:
            return jsonify({"error": "令牌无效"}), 401
    return decorated
```

#### 数据库会话管理
```python
from contextlib import contextmanager

@contextmanager
def get_db_session():
    """上下文管理器自动处理 commit/rollback"""
    session = db.session
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()
```

#### 权限过滤模式
```python
def build_assistant_filter(query, user_id):
    """动态构建权限过滤"""
    user = db.query(User).filter(User.id == user_id).first()
    
    # 特权用户全权限
    if user.username in ['yizhu001', 'GJD-A']:
        return query
    
    # 普通医助只能看自己的
    return query.filter(or_(
        PrescriptionRecord.assistant.is_(None),
        PrescriptionRecord.assistant == '',
        PrescriptionRecord.assistant == user.full_name
    ))
```

## Blueprint 注册 ⭐ 新增关键坑点

### 🚨 Flask Blueprint url_prefix 覆盖陷阱

**现象**: 蓝图自身定义了 `url_prefix='/api/reminders'`，但实际访问 `/api/reminders/` 返回 404，而 `/api/` 却能匹配该蓝图的路由

**根本原因**: `app.register_blueprint(blueprint, url_prefix='/xxx')` 参数会**完全覆盖**蓝图自身定义的 `url_prefix`！

**❌ 错误配置导致的问题**:\n```python
# followups.py
followups_bp = Blueprint('followups', __name__, url_prefix='/reminders')

# app.py (错误写法)\napp.register_blueprint(followups_bp, url_prefix='/api')\n# 结果：/api/ → followups_bp routes\n# 期望：/api/reminders/ → followups_bp routes\n# 实际：蓝图自定 prefix '/reminders' 被覆盖!\n```\n\n**✅ 正确做法**:\n\n#### 方案 A: 蓝图自定完整路径 (推荐)\n```python\n# followups.py - 定义完整前缀\nfollowups_bp = Blueprint('followups', __name__, url_prefix='/api/reminders')\n\n# app.py - 不要传 url_prefix\napp.register_blueprint(followups_bp)  # ✅ 使用蓝图自身 prefix\n```\n\n#### 方案 B: 注册时统一指定\n```python\n# followups.py - 只定义相对前缀\nfollowups_bp = Blueprint('followups', __name__, url_prefix='/reminders')\n\n# app.py - 完整指定最终路径\napp.register_blueprint(followups_bp, url_prefix='/api')  # 这会将 /reminders 替换为 /api!\n# ❌ 不推荐 - 容易混淆\n```\n\n**最佳实践**: 蓝图定义完整路径 (`/api/xxx`)，注册时不传递 `url_prefix` 参数

### 🔗 多路径别名支持 (前端兼容性)\n\n**场景**: 前端使用旧路径 `/api/followups/`，新系统改为 `/api/reminders/`\n\n**❌ 错误**: 直接修改后端路径，前端全部报错\n\n**✅ 正确**: 注册别名蓝图同时支持两个路径\n```python\n# app.py\nfrom api.v1.followups import followups_bp\n\n# 标准路径\napp.register_blueprint(followups_bp)  # /api/reminders/*\n\n# 别名路径 - 创建相同蓝图的不同实例\nfrom api.v1.followups import followups_bp as followups_alias\nfollowups_alias.name = 'followups_alias'  # 必须修改名字避免冲突\napp.register_blueprint(followups_alias, url_prefix='/api/followups')  # 别名\n```\n\n**验证**:\n```bash\n# 两个路径都应该工作\ncurl http://ip:port/api/reminders/pending   # ✅ \ncurl http://ip:port/api/followups/pending   # ✅\n```\n\n**注意事项**:\n- 别名蓝图的 `.name` 必须与原名不同，否则会导致端点命名冲突\n- 建议使用 `url_prefix` 显式控制别名的完整路径（而不是继承原蓝图）

## 常见外部库兼容性问题

### openpyxl Font API 版本差异

**现象**: `TypeError: 'StyleProxy' object is not callable`\n\n**原因**: openpyxl 2.x vs 3.x API 变化\n\n**❌ 旧版写法 (2.x)**:\n```python\ncell.font = cell.font(bold=True)\ncell.font = cell.font(color="FF0000")\n```\n\n**✅ 新版写法 (3.x+)**:\n```python\nfrom openpyxl.styles import Font\n\ncell.font = Font(bold=True)\ncell.font = Font(color="FF0000", bold=True)\n```\n\n### SQLAlchemy 1.4 insert 返回值

**现象**: `KeyError: 0` 或获取插入 ID 失败\n\n**✅ 正确写法**:\n```python\nresult = conn.execute(User.__table__.insert().values(username='test'))\nnew_id = list(result.inserted_primary_key)[0]  # ✅ SQLAlchemy 1.4+\n```\n\n---

## ⚡ 大项目并行执行策略：delegate_task 的正确用法

当核心代码需要子智能体并行处理时（如这次 7 个 Blueprint + 认证系统的同时开发）：

### 任务拆分原则

| 任务类型 | 子智能体数量 | 策略 |
|----------|-------------|------|
| 基础设施（config/database/models） | 1 | 顺序执行，依赖关系明确 |
| **认证系统 + 业务路由** | **2 个并行** | 文件集独立，可并行 |
| 启动调试 + 修复 | 1 | 需要全局上下文 |

### ❗ 重要教训：不要跨子智能体拆分同一逻辑层的任务

**错误做法**：把 6 个业务 Blueprint 分给 6 个子智能体并行写
- 问题：每个子智能体不知道其他 Blueprint 的路由，容易路径冲突
- 问题：import 依赖链复杂（Blueprint → auth → models → database）

**正确做法**：按依赖层次拆分
```
第一层（1 子智能体）：auth.py + api/v1/auth.py（认证系统）
第二层（1 子智能体）：所有业务 Blueprint（按顺序逐一创建）
第三层（1 子智能体）：启动调试 + 修复
```

### 终端超时环境下的断点续传

当 `terminal()` 命令持续超时（`BLOCKED: Command timed out`）时：

1. **纯文件操作**：所有代码创建/修改用 `write_file` + `patch` 完成
2. **语法检查替代运行测试**：用 `py_compile` 替代实际运行
```python
import py_compile, pathlib
for f in pathlib.Path('.').rglob('*.py'):
    if '__pycache__' not in str(f):
        py_compile.compile(str(f), doraise=True)
```
3. **子智能体中断不丢进度**：子智能体即使超时中断，已写的文件内容会保留
4. **恢复策略**：检查文件系统状态 → 对比预期 → 从断点继续补完

## ⭐ 本次新增：从 psycopg2 原生 SQL → SQLAlchemy ORM 完整迁移经验

### 场景
原系统使用 `psycopg2` + 原生SQL，2354行单体 app.py，需要迁移为 App Factory + Blueprint + SQLAlchemy ORM。

### 阶段一：auth.py 重写（psycopg2 → SQLAlchemy）

**❌ 旧做法**：`cursor.lastrowid`（SQLite API，PostgreSQL 不兼容）
```python
cursor.execute("INSERT INTO users (...) VALUES (...)")
user_id = cursor.lastrowid  # ❌ PostgreSQL 报错！
```

**✅ 新做法**：SQLAlchemy flush
```python
new_user = User(username=username, password_hash=password_hash)
db.session.add(new_user)
db.session.flush()
user_id = new_user.id  # ✅ 兼容所有数据库
```

### 阶段二：Base 类统一（★ 最重要的陷阱）

```python
# ❌ 错误：创建两个独立的 Base
# database.py
from sqlalchemy.orm import declarative_base
Base = declarative_base()  # Base A — db.create_all() 找不到模型

# models/base.py
from sqlalchemy.ext.declarative import declarative_base
Base = declarative_base()  # Base B

# ✅ 正确：统一使用 db.Model
# database.py
from flask_sqlalchemy import SQLAlchemy
db = SQLAlchemy()

# models/base.py
from database import db
Base = db.Model  # ✅ 统一继承
```

### 阶段三：模型注册时机

```python
def init_db(app):
    db.init_app(app)
    with app.app_context():
        # ✅ 关键：必须在 create_all 前导入所有模型文件！
        import models.user
        import models.role
        import models.prescription
        import models.log
        db.create_all()
```

### 阶段四：config.py 密钥管理（截断陷阱）

**现象**：文件内容被截断为 `SECRET_KEY=os.env...EY')`
**原因**：某些工具写入含敏感信息的 `.py` 文件时混淆/截断
**修复**：整文件重写，不用局部 patch
```python
# ✅ 正确
SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-fallback'
JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or 'dev-fallback'
DB_PASSWORD = os.environ.get('DB_PASSWORD') or 'dev-fallback'
SQLALCHEMY_DATABASE_URI = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
# ❌ 绝不要用 *** 占位符
```

### 阶段五：Blueprints 路由注册与冲突检查

**注册模式**（本次采用）：
```python
# api/v1/auth.py — Blueprint 只定义相对路径
auth_bp = Blueprint('auth_bp', __name__)

# app.py — 注册时统一加 url_prefix
app.register_blueprint(auth_bp, url_prefix='/api/auth')
app.register_blueprint(prescriptions_bp, url_prefix='/api')
app.register_blueprint(roles_bp, url_prefix='/api')
app.register_blueprint(stats_bp, url_prefix='/api')
```

**冲突检测方法**：
```python
import re
# 收集所有 Blueprint 中的路由
bp_match = re.search(r'(\w+)_bp\s*=\s*Blueprint\(', text)
if bp_match:
    routes = re.findall(r"@\w+_bp\.route\(['\"]([^'\"]+)['\"]", text)
    # 加上 url_prefix 检查完整路径是否重复
```

### 阶段六：运行时修复范例（NoneType 迭代错误）

**现象**：`api/reminders` 返回 `{'error': "argument of type 'NoneType' is not iterable"}`
**原因**：`to_dict()` 中 `pickup_date` 为 `None`，但后续代码 `' ' in pickup_date_str` 直接处理字符串
```python
# ❌ 错误：pickup_date 可能为 None
pickup_date_str = latest.get('pickup_date', '')

# ✅ 正确：先确保不是 None
pickup_date_str = latest.get('pickup_date') or ''
if not pickup_date_str:
    continue  # 跳过无取药日期的记录
```

## 验证清单

### 数据完整性
- [ ] 逐表比对记录数 (`SELECT COUNT(*)`)
- [ ] 抽样验证关联关系正确性
- [ ] 检查特殊字符/编码是否乱码
- [ ] 日期格式是否正确转换

### API 兼容性
- [ ] 所有路由路径一致
- [ ] 请求方法相同 (GET/POST/PUT/DELETE)
- [ ] JSON 响应结构一致
- [ ] 错误码保持一致

### 性能基准
- [ ] 列表查询 < 1s (含分页)
- [ ] 单条详情 < 200ms
- [ ] 复杂过滤 < 2s

## ⚡ 大规模融合项目执行策略（从本次经验总结）

### 核心问题：如何应对终端超时/不可用环境？

**场景**: 某些 Shell 环境（如受限服务器）无法执行 `terminal` 命令（`BLOCKED: Command timed out`），但文件读写正常。

**策略**: 纯文件操作模式
```bash
# ❸ 不要依赖 terminal 来测试或其他
# 改用 Python 语法检查 (py_compile) 
python3 -c "
import py_compile, pathlib
errors = []
for f in pathlib.Path('.').rglob('*.py'):
    try:
        py_compile.compile(str(f), doraise=True)
    except py_compile.PyCompileError as e:
        errors.append((str(f), str(e)))
print(f'OK: {len(list(pathlib.Path(\".\").rglob(\"*.py\")))-len(errors)}, ERR: {len(errors)}')
for p, e in errors: print(f'{p}: {e}')
"
```

### 并行执行模式：delegate_task 的正确用法

当核心代码需要被多个子智能体并行处理时：

| 任务 | 子智能体数量 | 策略 |
|------|-------------|------|
| 基础设施搭建（config/database/models） | 1 | 顺序执行，依赖关系明确 |
| **核心业务路由**（6+ Blueprint） | **1 个** | **按文件顺序逐一创建**，避免路由冲突 |
| 认证系统 + 业务路由 | **并行 2 个** | 独立的文件集，可并行 |
| 启动调试 + 修复 | 1 | 需要全局上下文 |

**经验教训**: 对于跨文件有 import 依赖的项目（Blueprint → auth → models → database），建议：
1. 先在一个子智能体中完成所有基础设施 + 核心认证
2. 统一在一个子智能体中按顺序创建所有 Blueprint
3. 最后用一个子智能体修复启动问题

### 常见 Python 3.6 兼容约束

```bash
# SQLAlchemy 1.4+ 不兼容 Python 3.6！
SQLAlchemy>=1.3.0,<1.4.0
Flask>=2.0.0,<3.0.0
Flask-SQLAlchemy>=2.5.1,<3.0.0
PyJWT>=2.0.0,<3.0.0
```

### 对 `config.py` 的截断陷阱

**现象**: 文件内容被截断 `SECRET_KEY=os.env...EY')` 
**原因**: 某些工具在写入包含敏感信息的 `.py` 文件时会混淆/截断
**修复**: 整文件重写，不使用局部 patch

## 数据库模型注册关键点

### `Base` 类统一是核心

```python
# ❌ 错误: 创建两个独立的 Base
# database.py
from sqlalchemy.orm import declarative_base
Base = declarative_base()  # Base A

# models/base.py
from sqlalchemy.ext.declarative import declarative_base
Base = declarative_base()  # Base B — db.create_all() 无法发现这些模型！

# ✅ 正确: 统一使用 Flask-SQLAlchemy 的 db.Model
# database.py
from flask_sqlalchemy import SQLAlchemy
db = SQLAlchemy()

# models/base.py
from database import db
Base = db.Model
```

### 在 `init_db()` 中注册模型

```python
def init_db(app):
    db.init_app(app)
    with app.app_context():
        # ✅ 关键：必须在 create_all 前导入所有模型文件
        import models.user
        import models.role  
        import models.prescription
        import models.log
        db.create_all()
```

## config.py 密钥管理

```python
# ✅ 正确写法：从环境变量读取
SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-fallback-key'
JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or 'dev-fallback-jwt-key'
DB_PASSWORD = os.environ.get('DB_PASSWORD') or 'dev-fallback-password'

SQLALCHEMY_DATABASE_URI = (
    f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)
# ❌ 不要用 *** 占位符 — 会直接导致连接失败
```

## Blueprint 路由冲突检测

```python
# 检测不同 Blueprint 间的路径冲突（重要！）
import re
text = f.read_text()
bp_match = re.search(r'(\w+)_bp\s*=\s*Blueprint\(', text)
if bp_match:
    routes = re.findall(r"@\w+_bp\.route\(['\"]([^'\"]+)['\"]", text)
    # 结合 url_prefix 计算完整路径
```

**常见冲突**: 两个 Blueprint 都定义了同一个路径（如 `/assistants`），但 url_prefix 不同时不会冲突。关键检查实际完整路径。

## 项目进度跟踪

对于跨会话的多阶段大型重构，使用 todo 工具记录阶段状态比依赖 memory 更可靠：

```python
todo(todos=[
    {"id": "phase1", "content": "基础设施搭建", "status": "completed"},
    {"id": "phase2", "content": "认证系统重构", "status": "completed"},
    ...
])
```

## 常见陷阱

| 问题 | 表现 | 解决方案 |
|------|------|----------|
| 外键约束失败 | `FOREIGN KEY CONSTRAINT VIOLATED` | 使用 ID 映射，先迁移主表再关联表 |
| 序列未重置 | `duplicate key value` | `ALTER SEQUENCE xxx RESTART WITH 1` |
| 时区问题 | 时间偏差 8 小时 | PostgreSQL 统一使用 UTC |
| DECIMAL 精度丢失 | 金额显示错误 | SQLite DECIMAL→PostgreSQL NUMERIC(n,m) |
| NULL 处理差异 | 查询结果不一致 | SQLite 的空字符串 vs NULL 需统一 |
| **API 字段不一致** | **部分端点缺失字段导致前端显示 `-`** | **遍历所有蓝图对比返回字典结构** |

### ⚠️ API 响应字段完整性验证 (新增关键测试项)

**典型场景**: 
- 旧代码 (SQLite) 某些端点已包含某字段 (如 `patient_phone`)
- 新重构的代码 (Blueprints) 遗漏该字段
- 表现：部分页面正常，特定功能模块显示为 `-`

**排查步骤**:
```bash
# 1. 列出所有路由对应的 handler
grep -rn "@.*\.route\(" backend/api/v1/*.py

# 2. 逐个测试 API 返回结构
curl http://localhost:5000/api/prescriptions/?limit=1 | jq '.[0] | keys'
curl http://localhost:5000/api/reminders | jq '.[0] | keys'
curl http://localhost:5000/api/follow-up | jq '.[0] | keys'

# 3. 对比期望字段与实际返回
# 期望：两个接口都应包含 patient_phone
# 发现：/api/prescriptions ✅ /api/reminders ❌ /api/follow-up ❌
```

**修复方法**: 统一所有端点的响应字典结构
```python
# ❌ 问题代码 - 遗漏 patient_phone
patient_data = {
    'id': record.id,
    'patient_name': record.patient_name,
    # ... 其他字段
}

# ✅ 修复 - 显式添加或默认值
patient_data = {
    'id': record.id,
    'patient_name': record.patient_name,
    'patient_phone': record.patient_phone or '',  # 关键！
    # ... 其他字段
}
```

**预防策略**:
1. 建立标准响应结构模板，所有新 Blueprint 必须遵循
2. 代码审查时对比前后端接口文档
3. 自动化测试验证关键字段存在性
4. 优先复用 `prescriptions.py` 等核心蓝图的返回结构作为参考模板

## ⭐ 关键：权限系统数据库初始化（迁移常见缺失）

### 现象
系统能正常启动、登录成功，但所有需要 `@permission_required` 的 API 都返回 `403 权限不足`，即使 admin 用户。

**原因**: 从 SQLite 迁移到 PostgreSQL 时：
1. `permissions` 表为空 — 没有创建任何权限记录
2. `role_permissions` 关联表为空 — 角色没有关联任何权限
3. `@permission_required('user:read')` 装饰器实时查数据库 → 查不到 → 返回 403

### 修复流程

```python
# 在迁移脚本中初始化权限数据
from database import db
from models import Role, Permission

def init_permissions():
    """初始化默认权限和角色权限分配"""
    session = db.session
    
    # 1. 创建所有需要的权限
    permissions_to_create = [
        ('user:read', '查看用户'),
        ('user:create', '创建用户'),
        ('user:update', '更新用户'),
        ('user:delete', '删除用户'),
        ('role:read', '查看角色'),
        ('role:create', '创建角色'),
        ('role:update', '更新角色'),
        ('role:delete', '删除角色'),
    ]
    
    for perm_name, perm_desc in permissions_to_create:
        if not session.query(Permission).filter_by(name=perm_name).first():
            session.add(Permission(name=perm_name, description=perm_desc))
    
    session.flush()
    
    # 2. 给 admin 角色分配所有权限
    admin_role = session.query(Role).filter_by(name='admin').first()
    if admin_role:
        all_perms = session.query(Permission).all()
        for p in all_perms:
            if p not in admin_role.permissions:
                admin_role.permissions.append(p)
    
    session.commit()
```

### 验证
```bash
# admin 用户应该返回 200，非 admin 用户返回 403
TOKEN=$(curl -s http://localhost:8080/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"admin123"}' | python3 -c "import sys,json;print(json.load(sys.stdin).get('token',''))")
curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/api/auth/users \
  -H "Authorization: Bearer $TOKEN"
# 期望输出: 200
```

### 预防
在迁移脚本中增加 `init_permissions()` 调用，确保迁移完成后权限系统立即可用。如果 `roles` 表也从零创建，需要同时创建 `admin`/`assistant`/`pharmacy` 等基本角色。

---

## 生产部署要点 ⭐ 新增

### Gunicorn 绑定地址选择

**❌ 错误**: 只绑定 localhost
```bash
python3 -m gunicorn --bind 127.0.0.1:5000 app:app
# 结果：公网无法访问!
```

**✅ 正确**: 绑定所有网卡
```bash
python3 -m gunicorn --bind 0.0.0.0:5000 app:app
# 结果：本地和公网均可访问
```

### Nginx 反向代理方案替代

**问题场景**: `/etc/nginx/conf.d/default.conf` 存在默认 server 块拦截请求

**症状**:
- Nginx 配置文件中写入自定义 80 端口规则无效
- 系统级 nginx.conf 修改风险高

**✅ 解决方案**: 直接使用 Gunicorn 监听非标准端口
```bash
# 放弃 Nginx 80 端口方案
# 改用 Gunicorn + 防火墙开放端口
sudo firewall-cmd --permanent --add-port=5000/tcp
sudo firewall-cmd --reload

# 公网访问：http://your-ip:5000
```

### 大型 JSON 响应优化

**问题**: 大结果集 (如 3000+ 条处方记录) 返回约 2.3MB JSON，导致测试工具管道溢出

**✅ 策略 1: API 层强制分页**
```python
@app.route('/api/prescriptions/')
def list_prescriptions():
    limit = min(request.args.get('limit', 50, type=int), 200)  # 限制最大值
    offset = request.args.get('offset', 0, type=int)
    
    query = db.query(PrescriptionRecord).limit(limit).offset(offset)
    ...
```

**✅ 策略 2: 统计与详情分离**
```python
# /api/prescriptions/statistics → 返回聚合数据 (轻量)
# /api/prescriptions/?limit=50 → 返回列表 (分页)
# /api/prescriptions/{id} → 返回单条详情
```

### systemd 服务稳定性

如果需长期无人值守运行，避免仅用背景进程：
```ini
# /etc/systemd/system/gaofang-v2.service
[Unit]
Description=Gaofang Management System V2
After=network.target postgresql.service

[Service]
User=root
WorkingDirectory=/root/projects/gaofang-v2/backend
Environment="PYTHONUNBUFFERED=1"
ExecStart=/usr/bin/python3 -m gunicorn \
    --bind 0.0.0.0:5000 \
    --workers 4 \
    --threads 2 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile - \
    app:app

Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

然后执行:
```bash
sudo systemctl daemon-reload
sudo systemctl enable gaofang-v2
sudo systemctl start gaofang-v2
sudo systemctl status gaofang-v2
```

### ⭐ 前端页面集成 (API+SPA 混合部署)

**问题场景**: Flask API 服务根路径只返回 JSON，无法直接访问前端界面

**症状**: 访问 `http://ip:port/` 显示 `{"message": "...", "endpoints": {...}}` 而非网页

**❌ 错误做法**: 认为 API 服务就应该返回 JSON，放弃前端集成

**✅ 解决方案**: 配置 Flask 静态文件服务和根路由重定向

#### 步骤 1: 创建静态资源目录
```bash
mkdir -p ~/projects/gaofang-v2/backend/static
cp ~/projects/MySQL-gaofang/index.html ~/projects/gaofang-v2/backend/static/
# 如有其他资源也需复制
cp -r ~/projects/MySQL-gaofang/assets/* ~/projects/gaofang-v2/backend/static/
```

#### 步骤 2: 修改 Flask 应用配置
```python
from flask import Flask, jsonify, send_from_directory  # 导入 send_from_directory

def create_app(config_class=Config):
    """Application factory"""
    # 关键：指定 static_folder 和 static_url_path
    app = Flask(__name__, static_folder='static', static_url_path='/static')
    
    app.config.from_object(config_class)
    ...
```

#### 步骤 3: 重写根路由返回 HTML
```python
# ❌ 旧代码 - 只返回 JSON
@app.route('/')
def index():
    return jsonify({
        "message": "Gaofang Management System V2 API",
        "version": "2.0.0"
    })

# ✅ 新代码 - 返回前端页面
@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')
```

#### 步骤 4: 确保 CORS 允许跨域
```python
from flask_cors import CORS

CORS(app, resources={r"/api/*": {"origins": "*"}})
# 注意：只开放 /api/* 避免暴露整个站点
```

#### 验证检查
```bash
# 验证前端加载
curl -s http://localhost:5000/ | grep "<!DOCTYPE html>"

# 验证 API 仍可用
curl -s http://localhost:5000/api/prescriptions/?limit=1

# 验证静态资源可访问
curl -s http://localhost:5000/static/favicon.ico -o /dev/null -w "%{http_code}"
```

#### 重启服务使更改生效
```bash
# Gunicorn 方式
sudo systemctl restart gaofang-v2

# 或直接重启后台进程
kill $(lsof -t -i:5000)
cd ~/projects/gaofang-v2/backend && python3 -m gunicorn --bind 0.0.0.0:5000 app:app &
```

**注意事项**:
- Flask `static_folder` 默认为 `static`，但建议显式指定以避免歧义
- `send_from_directory` 比 `send_file` 更安全（自动防御路径遍历攻击）
- 若前端有路由 (Vue Router/React Router)，需注意刷新 404 问题
- Nginx 反向代理时需额外配置 `try_files $uri /index.html`