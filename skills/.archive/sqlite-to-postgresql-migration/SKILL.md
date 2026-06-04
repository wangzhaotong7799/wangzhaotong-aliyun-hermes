---
title: SQLite 到 PostgreSQL 数据迁移指南
description: 使用 SQLAlchemy 完成 SQLite 到 PostgreSQL 的完整数据迁移工作流程，处理 ID 重映射、外键约束和 schema 差异
name: sqlite-to-postgresql-migration
tags:
  - database
  - migration
  - sqlalchemy
  - postgresql
  - sqlite
version: 1.0
author: Hermes Agent
date_created: 2026-04-24
---

# SQLite 到 PostgreSQL 数据迁移完整流程

## 概述

使用 SQLAlchemy 进行生产级数据库从 SQLite 到 PostgreSQL 迁移的方法论，确保数据完整性，处理 ID 重映射和外键关系。

## 适用场景

- 遗留系统现代化改造 (SQLite → PostgreSQL)
- 开发环境到生产环境的数据库升级
- 数据库引擎切换
- 多租户系统整合

## 前置条件

```bash
# Python 包 (兼容 Python 3.6+)
pip install flask==2.0.3 sqlalchemy==1.4.46 psycopg2-binary==2.9.9
```

## 核心挑战与解决方案

### 挑战 1: 自增 ID 行为不一致

**问题**: SQLite 的 AUTOINCREMENT 和 PostgreSQL 的 SERIAL 即使对相同顺序的插入也生成不同 ID。

**方案**: 不要保留旧 ID。让 PostgreSQL 自动生成新 ID 并建立映射表。

```python
id_map = {}  # old_id -> new_id

for row in old_rows:
    result = conn.execute(NewModel.__table__.insert().values(...))
    new_id = list(result.inserted_primary_key)[0]
    id_map[row['old_id']] = new_id
```

### 挑战 2: SQLAlchemy 1.4 API 差异

**问题**: `result.inserted_primary_key` 返回的是类似元组的对象，需要特殊处理。

**方案**: 先转换为列表，再按索引访问。

```python
# ❌ 错误 - 会报 KeyError: 0
new_id = dict(result.inserted_primary_key)[0]

# ✅ 正确 - SQLAlchemy 1.4 返回命名列
new_id = list(result.inserted_primary_key)[0]

# 如果主键未返回的回退方案
if new_id is None:
    new_id_result = conn.execute(text("SELECT currval('tablename_id_seq')")).fetchone()
    new_id = new_id_result[0]
```

### 挑战 3: 外键约束顺序

**问题**: 父记录不存在时无法插入子记录。

**方案**: 按依赖顺序插入：

1. 无外键的表 (permissions, roles, users)
2. 关系/连接表 (user_roles, role_permissions)
3. 引用父表的子表 (prescription_records)
4. 审计/日志表 (status_change_logs)

### 挑战 4: Schema 漂移（模型与实际库结构不一致）

**问题**: ORM 模型与实际数据库结构不匹配（遗留系统常见问题）。

**方案**: 编写迁移代码前先验证实际 schema：

```bash
# 检查 SQLite schema
sqlite3 source.db ".schema tablename"

# 检查第一行数据结构  
sqlite3 source.db "SELECT * FROM tablename LIMIT 1;"
```

然后再更新 SQLAlchemy 模型。

## 完整迁移脚本模板

```python
#!/usr/bin/env python3
"""
生产级 SQLite 到 PostgreSQL 迁移脚本
策略：Drop + Recreate schema，让 PG 自动生成 ID
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

import sqlite3
from datetime import datetime
from sqlalchemy import create_engine, text
from models import Base, User, Role, Permission, user_roles, role_permissions, PrescriptionRecord

def migrate_data():
    print("=" * 60)
    print("🔄 SQLite → PostgreSQL 迁移工具")
    print("=" * 60)
    
    start_time = datetime.now()
    
    # 连接数据库
    sqlite_conn = sqlite3.connect('/path/to/source.db')
    sqlite_conn.row_factory = sqlite3.Row
    
    pg_engine = create_engine(
        'postgresql://USER:PASSWORD@localhost/DATABASE',
        pool_pre_ping=True,
        echo=False
    )
    
    # 强制重建 schema（模型更改后很重要）
    print("\n创建 PostgreSQL 表...")
    Base.metadata.drop_all(pg_engine)
    Base.metadata.create_all(pg_engine)
    print("  ✓ 表创建完成\n")
    
    try:
        with pg_engine.begin() as conn:
            sqlite_cur = sqlite_conn.cursor()
            
            # 步骤 1: 迁移独立表（无 FK 依赖）
            print("[1/N] 迁移 permissions...")
            sqlite_cur.execute("SELECT name, description FROM permissions")
            for row in sqlite_cur.fetchall():
                conn.execute(Permission.__table__.insert().values(
                    name=row[0], description=row[1]))
            print(f"  ✓ 已迁移 permissions")
            
            print("\n[2/N] 迁移 roles...")
            sqlite_cur.execute("SELECT id, name, description FROM roles")
            role_id_map = {}
            for row in sqlite_cur.fetchall():
                result = conn.execute(Role.__table__.insert().values(
                    name=row[1], description=row[2]))
                new_id = list(result.inserted_primary_key)[0]
                role_id_map[row[0]] = new_id
            
            # 步骤 2: 使用 ID 映射迁移关系表
            print("\n[3/N] 迁移 relationships...")
            sqlite_cur.execute("SELECT role_id, permission_id FROM role_permissions")
            for row in sqlite_cur.fetchall():
                conn.execute(role_permissions.insert().values(
                    role_id=role_id_map[row['role_id']],
                    permission_id=row['permission_id']))
            
            print(f"\n✅ 迁移完成，耗时 {(datetime.now()-start_time).total_seconds():.1f}秒")
            
    except Exception as e:
        print(f"\n❌ 迁移失败：{e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    success = migrate_data()
    exit(0 if success else 1)
```

## 常见陷阱与调试

| 错误 | 原因 | 解决方案 |
|------|------|----------|
| `duplicate key value violates unique constraint` | 运行间表未清空 | 在迁移前添加 `drop_all()` 或 `DELETE FROM` |
| `foreign key constraint violated` | 子记录先于父记录插入 | 调整顺序：先父表后子表 |
| `No item with that key` | 访问 `inserted_primary_key` 方式错误 | 使用 `list(result.inserted_primary_key)[0]` |
| `Unconsumed column names` | 模型缺少数据中存在的字段 | 更新模型定义 |
| `column X does not exist` | 模型已更新但表未重建 | 在 `create_all()` 前添加 `drop_all()` |

## 最佳实践

1. **始终备份**源数据库
2. **验证 schema** 再写迁移代码
3. **先用子集测试** (LIMIT 100)
4. **保留 ID 映射**给关系表用
5. **使用事务** (`with pg_engine.begin() as conn:`)
6. **每步记录进度**便于排查
7. **事后校验数量** (源 vs 目标)

## 验证清单

迁移完成后：

```sql
-- 验证记录数一致
SELECT 
    (SELECT COUNT(*) FROM source.permissions) as source_perms,
    (SELECT COUNT(*) FROM target.permissions) as target_perms;

-- 检查随机样本数据完整性
SELECT * FROM prescription_records ORDER BY RANDOM() LIMIT 5;

-- 验证必填字段无 NULL
SELECT COUNT(*) FROM users WHERE username IS NULL;
```

## 实战案例

**项目**: 膏方管理系统 V2 升级  
**数据量**: 4,790 条记录 (含 3,438 条核心处方记录)  
**耗时**: 6.2 秒  
**迭代次数**: 8 次（解决各种兼容性问题）

关键经验：
- SQLite 和 PostgreSQL 的序列行为完全不同
- SQLAlchemy 1.4 的 API 细节需要注意
- 一定要先查实际 schema 而不是依赖文档
- drop_all + create_all 可以强制刷新 schema

## 相关技能

- `legacy-system-safe-refactoring` - 遗留系统安全重构方法论
- `flask-app-startup-troubleshooting` - Flask 应用启动排查
- `centos-python36-deployment` - CentOS/Python 3.6 部署指南

---

## 补充：Blueprint URL 路由问题

### 常见错误

```python
# ❌ 会导致 /api/api/auth/login 双重重叠
auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')
app.register_blueprint(auth_bp, url_prefix='/api')  # 又加了/api!

# ✅ 正确方案 1: 蓝图内不带 /api/
auth_bp = Blueprint('auth', __name__, url_prefix='/auth')
app.register_blueprint(auth_bp, url_prefix='/api')

# ✅ 正确方案 2: 注册时不额外加前缀
auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')
app.register_blueprint(auth_bp)  # 不再次加前缀
```

---

## 补充：生产环境部署要点

### Gunicorn Worker 配置

根据服务器内存调整：
```bash
# 小内存 (512MB): 2 workers, 1 thread
gunicorn --bind 127.0.0.1:5000 --workers 2 --threads 1 app:app

# 中等内存 (2GB): 4 workers, 2 threads  
gunicorn --bind 127.0.0.1:5000 --workers 4 --threads 2 app:app

# 大内存 (8GB+): 8 workers, 4 threads
gunicorn --bind 127.0.0.1:5000 --workers 8 --threads 4 app:app
```

### Nginx 配置文件放置规则

**CentOS/RHEL Nginx**:
```
/etc/nginx/conf.d/*.conf       # 在 http {} 块内被 include ✓
/etc/nginx/default.d/*.conf    # 也在 http {} 块内但可能冲突
/etc/nginx/sites-enabled/*     # Ubuntu 风格，CentOS 不使用
```

检查方式：
```bash
grep "include" /etc/nginx/nginx.conf | grep conf.d
```

如果看到 `include /etc/nginx/conf.d/*.conf;` 说明该目录生效。

### Nginx Server Block 位置要求

server {} 指令必须在 http {} 块内！错误会报：
```
nginx: [emerg] "server" directive is not allowed here
```

解决：确认 nginx.conf 的 include 语句加载你的配置在 http {} 范围内。