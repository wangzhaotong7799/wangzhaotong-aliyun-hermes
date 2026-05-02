---
name: legacy-system-safe-refactoring
description: 遗留系统安全重构方法论 - 确保零功能丢失的技术升级流程
version: 1.0.0
author: Hermes Agent
tags: [refactoring, migration, safe-upgrade, legacy-system]
toolsets_required: ['file', 'terminal']
---

# 🔄 遗留系统安全重构方法论

## 📋 概述

本技能记录了**在不改变业务功能的前提下进行技术栈升级**的标准流程。适用于需要将旧系统（如单体 Flask+SQLite）迁移到新技术（如模块化 +PostgreSQL）但不影响现有用户和功能的场景。

**核心原则**: 零功能丢失、零新增功能、隔离运行、完整回归测试

---

## 🎯 适用场景

使用此方法当您需要：

- ✅ 升级技术栈（Python 版本、框架、数据库等）
- ✅ 重构代码结构（单体→模块化、同步→异步）
- ✅ 提升性能或安全性而不改业务逻辑
- ✅ 保持新旧系统并行运行对比测试
- ✅ 需要 100% 功能兼容性保证

**不适用场景:**
- ❌ 功能增强或新特性开发
- ❌ 业务流程改造
- li 用户体验优化（UI/UX 改动）

---

## 📐 六阶段执行流程

### 阶段 0: 完整功能清单梳理 ⚠️ (最关键)

**目标**: 建立详尽的功能基线，作为后续验收标准

#### Step 0.1: API 接口枚举
```bash
# 自动提取所有路由端点
grep -n "@app.route\|@router\." app.py | sort

# 统计接口数量和方法
grep -oE '@(GET|POST|PUT|DELETE).*\([^)]+\)' *.py | cut -d'"' -f2 | sort | uniq -c
```

**输出格式示例:**
```markdown
### 认证模块 (7 个端点)
| # | 方法 | 路径 | 权限 | 功能描述 |
|---|------|------|------|----------|
| 1 | POST | /api/auth/login | 无需 | 用户登录返回 JWT |
| ...
```

#### Step 0.2: 前端功能逆向工程
```bash
# 提取 JavaScript 函数定义
grep -oE 'function\s+[a-zA-Z_]+|async function\s+[a-zA-Z_]+' index.html | sort -u

# 查找事件绑定
grep -oE '\.on\([a-zA-Z-]+\)|addEventListener\(\'[^\']+\'' *.html | sort -u
```

**关键问题清单:**
- 有多少个页面？每个页面的功能按钮有哪些？
- Modal/弹窗有哪些类型？触发条件是什么？
- 数据可视化图表有几个？数据来源是哪些 API？
- 表单校验规则是什么？
- Excel/PDF导出有几种格式？列顺序如何？

#### Step 0.3: 数据库结构分析
```python
# SQLite 表结构导出
import sqlite3
conn = sqlite3.connect('your.db')
cursor = conn.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
for table in cursor.fetchall():
    cursor.execute(f"PRAGMA table_info({table[0]})")
    print(cursor.fetchall())
```

**记录内容:**
- 每张表的字段、类型、约束
- 索引定义
- 外键关系
- 触发器（如果有）

#### Step 0.4: 核心业务逻辑提取
```python
# 伪代码模板，逐行注释关键逻辑

# 状态流转规则
if old_status == "欠药" and new_status == "未取":
    record_log(operator, reason)  # 必须记录日志
    
# 自动计算规则
if status == "已邮寄":
    days_from_prescription_to_shipping = shipping_time - date  # 必填
    
# 业务判断规则  
if 7 <= days_since_notification <= 30:
    follow_up_status = "待复诊"  # 自动设置
```

**最终产出**: `V1_FUNCTIONAL_SPEC.md` 文档，作为验收标准

---

### 阶段 1: 架构设计（保守策略）

#### 技术选型原则

| 维度 | V1 现状 | V2 选择 | 理由 |
|------|--------|--------|------|
| 语言 | Python 3.6 | Python 3.6 | **不升级，避免兼容问题** |
| Web 框架 | Flask | Flask Blueprint | 同框架仅改组织方式 |
| ORM | sqlite3 原生 | SQLAlchemy | 主流 ORM，向后兼容 |
| 数据库 | SQLite | SQLite → 可选 PostgreSQL | 优先保持 SQLite 降低风险 |
| 前端 | HTML+JS | **不变** | 零改动原则 |
| 认证 | JWT | JWT | 同机制 |

#### 项目结构模板
```
~/projects/{project}-v2/
├── backend/
│   ├── api/v1/              # 严格与 V1 路径一致
│   │   ├── __init__.py
│   │   ├── auth_bp.py       # 认证 Blueprint
│   │   ├── users_bp.py      # 用户管理
│   │   ├── prescriptions_bp.py
│   │   └── admin_bp.py      # 后台管理
│   ├── models/              # SQLAlchemy 模型
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── prescription.py
│   │   └── permission.py
│   ├── core/                # 通用工具
│   │   ├── db.py            # 数据库连接池
│   │   ├── jwt.py           # JWT 封装
│   │   ├── cache.py         # 可选缓存层
│   │   └── logger.py        # 日志配置
│   ├── config.py            # 环境配置
│   ├── app.py               # Flask 初始化
│   └── wsgi.py              # Gunicorn 入口
├── migrations/              # 数据库迁移脚本
│   ├── versions/
│   └── env.py
├── tests/                   # 回归测试
│   ├── test_auth.py
│   ├── test_api_compatibility.py
│   └── fixtures/
├── requirements.txt         # 依赖列表
└── run.sh                   # 启动脚本（默认端口 80）
```

---

### 阶段 2: 代码重构实施

#### 2.1 优先级排序

```python
IMPLEMENTATION_ORDER = [
    # 基础设施（必须先完成）
    ("config.py", "环境配置，数据库连接字符串"),
    ("core/db.py", "数据库连接池，Session 管理"),
    ("models/*.py", "ORM 模型定义"),
    
    # 核心功能（从简单到复杂）
    ("auth_bp.py", "认证模块，JWT 逻辑"),
    ("users_bp.py", "用户 CRUD，角色关联"),
    ("prescriptions_bp.py", "处方核心业务"),
    
    # 高级功能
    ("follow_up_bp.py", "复诊逻辑，自动计算"),
    ("admin_bp.py", "数据库备份恢复"),
    ("report_bp.py", "统计报表，Excel 导出"),
]
```

#### 2.2 Blueprint 模板
```python
# backend/api/v1/prescriptions_bp.py

from flask import Blueprint, request, jsonify, g
from sqlalchemy.orm import Session
from ..core.db import get_db_session
from ..models.prescription import Prescription
from ..core.auth import auth_required, permission_required

prescriptions_bp = Blueprint('prescriptions', __name__, url_prefix='/api/prescriptions')

@prescriptions_bp.route('', methods=['GET'])
@auth_required
@permission_required('prescription:read')
def list_prescriptions():
    """获取处方列表 - 完全兼容 V1 参数"""
    session: Session = get_db_session()
    
    # 提取查询参数（与 V1 保持一致）
    status = request.args.get('status')
    doctor = request.args.get('doctor')
    assistant = request.args.get('assistant')
    patient_name = request.args.get('patient_name')
    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('page_size', 50, type=int)
    
    # 构建查询
    query = session.query(Prescription)
    
    if status:
        query = query.filter(Prescription.status == status)
    if doctor:
        query = query.filter(Prescription.doctor == doctor)
    if patient_name:
        query = query.filter(Prescription.patient_name.ilike(f'%{patient_name}%'))
    
    # 分页（与 V1 行为一致）
    total = query.count()
    items = query.offset((page-1)*page_size).limit(page_size).all()
    
    return jsonify({
        'items': [prescription.to_dict() for prescription in items],
        'total': total,
        'page': page,
        'page_size': page_size
    })
```

**关键点:**
- ✅ URL 路径与 V1 完全相同
- ✅ 查询参数名称与顺序一致
- ✅ 返回 JSON 结构保持一致（必要时调整以匹配前端）
- ✅ 错误码和消息文本相同

#### 2.3 ORM 模型转换技巧
```python
# V1: sqlite3.Row
# SELECT * FROM prescription_records WHERE id = ?
# result = cursor.fetchone()  -> {'id': 1, 'date': '2024-01-01', ...}

# V2: SQLAlchemy
class Prescription(Base):
    __tablename__ = 'prescription_records'
    
    id = Column(Integer, primary_key=True)
    date = Column(Date, nullable=False)
    prescription_id = Column(String(50), unique=True, nullable=False)
    # ... 其他字段
    
    def to_dict(self):
        """转换为与 V1 相同的字典格式"""
        return {
            'id': self.id,
            'date': self.date.isoformat() if self.date else None,  # 注意日期格式化
            'prescription_id': self.prescription_id,
            # ... 确保所有字段名与 V1 一致
        }
```

---

### 阶段 3: 兼容性测试（严格回归）

#### 3.1 自动化工具

```python
# tests/test_api_compatibility.py

import requests

V1_BASE_URL = "http://localhost:5000"
V2_BASE_URL = "http://localhost:80"

TEST_CASES = [
    {
        "name": "login_success",
        "method": "POST",
        "path": "/api/auth/login",
        "data": {"username": "admin", "password": "test123"},
        "expected_code": 200,
        "validate_fn": lambda r1, r2: r1.json()['token'][:10] == r2.json()['token'][:10]
    },
    {
        "name": "list_prescriptions_filter",
        "method": "GET",
        "path": "/api/prescriptions",
        "params": {"status": "未取", "doctor": "丛东海"},
        "expected_code": 200,
        "headers": {"Authorization": "Bearer <token>"},
        "validate_fn": lambda r1, r2: len(r1.json()) == len(r2.json())
    },
    # ... 覆盖全部 48 个 API
]

def test_all_endpoints():
    failures = []
    for case in TEST_CASES:
        r1 = requests.request(case['method'], V1_BASE_URL + case['path'], 
                             data=case.get('data'), params=case.get('params'))
        r2 = requests.request(case['method'], V2_BASE_URL + case['path'],
                             data=case.get('data'), params=case.get('params'))
        
        assert r1.status_code == r2.status_code, f"{case['name']}: HTTP code mismatch"
        
        try:
            assert case['validate_fn'](r1, r2), f"{case['name']}: Response validation failed"
        except AssertionError as e:
            failures.append(f"{case['name']}: {e}")
    
    if failures:
        print("❌ 失败项:")
        for f in failures:
            print(f"  - {f}")
        return False
    else:
        print(f"✅ 所有 {len(TEST_CASES)} 个 API 兼容性测试通过！")
        return True
```

#### 3.2 前端手动验证清单

在浏览器中访问 V2 (端口 80)，逐项测试：

```markdown
- [ ] 登录页面正常显示
- [ ] 登录成功后跳转主页
- [ ] 处方列表加载成功，排序一致
- [ ] 筛选器工作正常（状态、医生、医助）
- [ ] 搜索框拼音搜索生效
- [ ] 点击编辑按钮弹出模态框
- [ ] 表单保存成功，无 JS 错误
- [ ] 分页切换正常
- [ ] 删除操作二次确认
- [ ] 复诊页面天数计算正确
- [ ] 统计图表渲染正确
- [ ] 导出 Excel 文件格式一致
- [ ] ... (继续直到覆盖所有界面交互)
```

---

### 阶段 4: 并行部署与灰度切流

#### 4.1 双端口运行配置

```bash
# ~/projects/MySQL-gaofang/run_v1.sh  (保持不变)
cd ~/projects/MySQL-gaofang
python3 app.py --port=5000

# ~/projects/gaofang-v2/run_v2.sh  (新建)
#!/bin/bash
cd ~/projects/gaofang-v2/backend
export FLASK_ENV=production
gunicorn --workers=4 --bind=0.0.0.0:80 wsgi:app
```

#### 4.2 Nginx 分流配置（可选）

```nginx
server {
    listen 80;
    server_name gaofang.example.com;
    
    location /api {
        # 灰度：10% 流量走 V2
        if ($random_uint % 100 < 10) {
            proxy_pass http://127.0.0.1:80;
        } else {
            proxy_pass http://127.0.0.1:5000;
        }
    }
    
    location / {
        root /var/www/html;
    }
}
```

---

### 阶段 5: 监控与回滚准备

#### 5.1 监控指标

```yaml
必须跟踪的指标:
  - API 响应时间对比 (P50/P90/P99)
  - 错误率对比 (按端点分组)
  - 404/405错误数（可能表示API不一致）
  - 前端 JS 异常上报
  
告警阈值:
  - V2 错误率 > V1 错误率 + 0.5% → 立即告警
  - V2 平均延迟 > V1 * 2 → 警告
```

#### 5.2 一键回滚脚本

```bash
#!/bin/bash
# stop_v2.sh

echo "正在停止 V2 服务..."
systemctl stop gaofang-v2
pkill -f "gunicorn.*wsgi"

echo "V2 已停止，流量全部回到 V1"

# 可选：清理 V2 日志
# rm -rf ~/projects/gaofang-v2/logs/*
```

---

## ⚠️ 常见陷阱与解决方案

### 陷阱 0: 依赖包环境兼容性问题 (实战经验)

**场景**: CentOS/AlmaLinux 8 默认 Python 3.6，官方 PGDG 仓库 404 错误

**问题表现:**
```bash
# PostgreSQL 15 安装失败
sudo yum install postgresql15-server
Error: Failed to download metadata for repo 'pgdg-common': 404

# psycopg2-binary 编译失败  
pip install psycopg2-binary==2.9.6
WARNING: Discarding ... (requires-python:>=3.6)
Command errored out with exit status 1
```

**解决方案:**
```bash
# Step 1: 清理冲突的 PGDG 仓库配置
# 检查 /etc/yum.repos.d/pgdg*.repo 文件并移除或禁用

# Step 2: 使用系统自带源 (PostgreSQL 13)
sudo yum install postgresql-server postgresql-contrib

# Step 3: 降级 psycopg2-binary 版本到兼容 py3.6 的版本
pip install psycopg2-binary==2.9.3  # 支持 py3.6 的最后稳定版
```

**技术选型参考表 (Python 3.6 环境):**
| 组件 | V1 现状 | V2 推荐 | 说明 |
|------|--------|--------|------|
| Flask | 2.0.x | 2.0.3 | 最后支持 py3.6 的稳定版 |
| SQLAlchemy | N/A | 1.4.46 | v2.0 的 declarative API 已在 1.4 稳定 |
| psycopg2-binary | N/A | 2.9.3 | py3.6 兼容版本 |
| PyJWT | 2.4.x | 2.4.0 | 保持原版本即可 |
| PostgreSQL | SQLite | 13.x | 官方 15.x 仓库不可用时降级方案 |

---

### 陷阱 1: 忽略隐性业务逻辑

**症状**: API 测试通过，但用户报告"某个功能坏了"

**案例**: V1 中有隐藏的业务规则，如"状态从 X 变 Y 时自动填充 Z 字段"

**解决**: 
- 仔细审查所有 `update`/`save`/`submit` 相关函数的完整逻辑
- 检查是否有数据完整性约束
- 录制用户操作流程，对比 V1/V2 的行为差异

### 陷阱 2: 日期/时间格式不一致

**症状**: 前端显示"Invalid Date"或图表渲染失败

**原因**: V1 返回 `"2024-01-01"`，V2 返回 `"2024-01-01T00:00:00Z"`

**解决**:
```python
# 强制统一格式
from datetime import date, datetime

def format_date_for_frontend(dt):
    if isinstance(dt, datetime):
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    elif isinstance(dt, date):
        return dt.strftime('%Y-%m-%d')
    return str(dt)
```

### 陷阱 3: 分页行为差异

**症状**: 最后一页数据缺失或重复

**原因**: V1 用 `LIMIT OFFSET`，V2 用了游标分页；或者总数计算逻辑不同

**解决**: 严格复制 V1 的分页实现细节

### 陷阱 4: 前端硬编码的 API 细节

**症状**: 明明 API 功能一样，但前端报错

**原因**: JavaScript 中写死了某些假设，如"response.data.items.length"

**解决**:
- 抓包对比 V1/V2 的完整响应体
- 检查前端对特殊值（null vs undefined vs ""）的处理

---

## 📊 成功指标

重构完成后应达到：

- ✅ 所有 48 个 API 100% 兼容（自动化测试通过）
- ✅ 前端无需任何修改即可连接 V2
- ✅ 用户无法察觉系统切换
- ✅ 性能至少持平（最好有提升）
- ✅ 代码可维护性显著改善（圈复杂度下降）

---

## 🔄 中断恢复机制设计（实战经验）

### 为什么需要？

在复杂的重构项目中，会话中断是必然的。如果没有完善的恢复机制，每次重启都要重新分析上下文，效率极低。

### 三层次恢复体系

#### Level 1: 状态检查点 (`.upgrade_checkpoint`)

```bash
# Project Progress Checkpoint
STATUS=READY_TO_START_STAGE2
CURRENT_PHASE=1
LAST_COMPLETED_TASK=T2-05
NEXT_TASK=T2-06

COMPLETED_STAGES=Stage0,Stage1
PENDING_STAGES=Stage2_3_4_5

CHECKPOINT_TIMESTAMP=2026-04-24T07:05:00+08:00
RESUME_INSTRUCTION="Continue from T2-06: Write migration script for prescription_records table"
```

**关键要素:**
- 当前阶段和最后完成的任务 ID
- 下一步要执行的任务
- 时间戳便于判断进度新鲜度
- 简明的恢复指令

#### Level 2: 团队工作日志 (`TEAM_LOG.md`)

```markdown
## 2026-04-24

### 07:00 - ✈️ 飞飞启动环境部署
- PostgreSQL 13.23 安装成功
- gaofang_v2 数据库创建 ✓
- 项目目录结构搭建完成 ✓

### 07:05 - 阶段 1 验收通过
[✅] PostgreSQL 服务运行正常
[✅] 数据库连接测试通过

### 下一步：⚡ 闪电进入阶段 2 - 数据库迁移
```

**好处**: 
- 记录每个阶段的实际执行人
- 发现什么问题 + 怎么解决的
- 可以追溯到具体的技术决策原因

#### Level 3: 详细执行计划 (`EXECUTION_PLAN.md`)

包含 7 个阶段、几十个具体任务的完整清单，每个任务都有：
- 验证标准（如何判断完成）
- 回滚方案（如果失败怎么办）
- 预计耗时（资源规划）

### 恢复流程模板

```bash
# Step 1: 查看最新检查点
cat /path/to/.upgrade_checkpoint

# Step 2: 阅读最近的团队日志
tail -50 TEAM_LOG.md

# Step 3: 找到下一个任务
grep "NEXT_TASK=" .upgrade_checkpoint

# Step 4: 查看该任务的详细说明  
grep -A 15 "NEXT_TASK_VALUE" EXECUTION_PLAN.md

# Step 5: 执行并更新日志
echo "### $(date '+%Y-%m-%d %H:%M') - 完成任务 X" >> TEAM_LOG.md
```

---

## 🎯 经验教训总结

**最重要的三条经验:**

1. **阶段 0（功能清单）的时间投入越充分，后期问题越少**
   - 建议花费总工期 20%-30% 在这个阶段
   - 宁可多花时间分析，也不要匆忙开始编码

2. **不要过度优化**
   - V1 能跑就不要改底层逻辑
   - 先追求"完全兼容"，再考虑"更优雅"
   - 数据库升级可以延后（保持 SQLite 也是选项）

3. **自动化测试是必须的**
   - 手动测试永远无法覆盖所有组合
   - 每次提交前运行兼容性测试
   - 保留测试用例作为文档

---

**最后提醒**: 重构的目的是让代码更容易维护和扩展，而不是为了炫技。如果某处 V1 的代码看起来很丑但没有 bug，就照着丑的样式复制过去 —— **稳定性永远是第一位的**。
