---
name: flask-api-business-logic-debugging
description: Flask API 业务逻辑调试方法论 - 实现累计计算、时间窗口统计、患者识别等复杂业务场景的系统方法
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [flask, api, business logic, debugging, sqlalchemy, python]
    related_skills: [systematic-debugging, test-driven-development]
---

# Flask API 业务逻辑调试方法论

在 Flask 应用中实现复杂业务逻辑时的系统调试方法和常见陷阱处理。

## 适用场景

- 需要实现累计计算、时间窗口统计等业务逻辑
- 多条件患者/实体识别和去重
- 跨表关联查询和数据聚合
- 前后端接口对接和数据格式校验

## 核心流程

### 1. 明确业务规则（最关键！）

**在写代码前先确认以下细节：**

```markdown
## 患者识别标准
- 必需条件：[ ] 姓名 [ ] 性别 [ ] 年龄 [ ] 电话号码
- 是否允许部分匹配？[ ] 是 / [x] 否
- 年龄会随时间变化吗？如何处理？

## 统计范围
- 统计周期：最近几天内的记录？[ ] 7 天 / [x] 3 天 + 当天
- 时间起点：以最后一条记录的日期为准
- 是否包含当前记录？[x] 是 / [ ] 否

## 计算公式
- 单位换算：每单位 = ______ 天
- 边缘情况：空值、负数、重复记录如何处理？
```

**实战经验：** 业务规则的细微理解差异会导致多次返工。例如"前 3 日内"可能理解为：
- ❌ 错误：前 3 天（不含当天）→ 漏计当天的取药
- ✅ 正确：包含最后取药日及前 3 天 → 共 4 天的窗口期

### 2. 先测试后端逻辑

在调用 API 之前，先在 Python 中验证数据查询：

```python
import subprocess
result = subprocess.run([
    'python3', '-c', '''
import sys
sys.path.insert(0, "/path/to/backend")

from flask import Flask
from database import db, get_db_session
from models import PrescriptionRecord

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "postgresql://..."
db.init_app(app)

with app.app_context():
    # 测试查询
    records = session.query(PrescriptionRecord).filter(
        PrescriptionRecord.patient_name == "张三"
    ).order_by(PrescriptionRecord.pickup_date.desc()).all()
    
    print(f"共{len(records)}条记录")
    total_qty = sum(r.quantity or 0 for r in records[:5])
    print(f"前 5 条总料数：{total_qty}")
'''
], capture_output=True, text=True)

print(result.stdout)
```

### 3. 患者识别最佳实践

#### 陷阱：年龄会随时间变化！

```python
# ❌ 错误：使用固定年龄匹配会导致漏计
db.query(User).filter(
    User.patient_name == name,
    User.age == age  # 历史记录的年龄可能不同！
)

# ✅ 正确：考虑年龄变化的匹配策略
# 方案 A: 不使用年龄字段
db.query(User).filter(
    User.patient_name == name,
    User.gender == gender,
    User.phone == phone  # 最可靠的标识符
)

# 方案 B: 使用范围匹配（如果必须用年龄）
from sqlalchemy import and_
db.query(User).filter(
    User.patient_name == name,
    User.gender == gender,
    and_(User.age >= current_age - 2, User.age <= current_age + 1)
)
```

#### 推荐的匹配策略

| 策略 | 优点 | 缺点 | 适用场景 |
|------|------|------|----------|
| 姓名 + 性别 | 简单 | 重名概率高 | 小型诊所 (<500 人) |
| 姓名 + 性别 + 电话 | 精确稳定 | 电话号码可能变更 | **生产环境首选** |
| 四字段全匹配 | 理论精确 | 年龄变化导致漏计 | ⚠️ 谨慎使用 |
| 唯一 ID（UUID） | 完美 | 需要数据库改造 | 新项目设计 |

### 4. 时间窗口统计实现

```python
from datetime import date, timedelta
from sqlalchemy import or_

def calculate_recent_total(record, db):
    """
    计算患者最近 4 天（含当天）的累计料数
    
    Args:
        record: 当前处方记录
        db: SQLAlchemy session
    
    Returns:
        (total_quantity, total_days) tuple
    """
    # 获取该患者的所有处方（按日期倒序）
    phone_filter = record.patient_phone or ""
    
    all_records = db.query(PrescriptionRecord).filter(
        PrescriptionRecord.patient_name == record.patient_name,
        PrescriptionRecord.gender == record.gender,
        # 电话号码精确匹配（NULL 视为空字符串）
        or_(
            PrescriptionRecord.patient_phone == phone_filter,
            (PrescriptionRecord.patient_phone.is_(None) & (phone_filter == ""))
        )
    ).order_by(PrescriptionRecord.pickup_date.desc()).all()
    
    if len(all_records) == 0:
        return (record.quantity or 0, 0)
    
    latest_record = all_records[0]
    latest_pickup_date = latest_record.pickup_date
    
    if latest_pickup_date:
        latest_date_obj = latest_pickup_date.date()
        
        # 计算起始点（前 3 日，共 4 天窗口）
        start_date = latest_date_obj - timedelta(days=3)
        
        # 累加窗口内的量
        total_qty = 0
        for p in all_records:
            if p.pickup_date:
                pickup_date_obj = p.pickup_date.date()
                if start_date <= pickup_date_obj <= latest_date_obj:
                    total_qty += (p.quantity or 0)
    else:
        total_qty = record.quantity or 0
    
    # 服用天数 = 总量 × 30 天/单位
    total_days = int(total_qty) * 30
    
    return (total_qty, total_days)
```

### 5. 常见调试技巧

#### 检查实际数据与预期是否一致

```bash
# 直接查询数据库验证
psql -U user -d dbname << EOF
SELECT 
    patient_name, 
    pickup_date::date, 
    quantity,
    SUM(quantity) OVER (
        PARTITION BY patient_name, gender 
        ORDER BY pickup_date DESC 
        ROWS BETWEEN 3 PRECEDING AND CURRENT ROW
    ) as rolling_sum
FROM prescription_record
WHERE patient_name = '张三'
ORDER BY pickup_date DESC
LIMIT 10;
EOF
```

#### 验证 API 返回数据

```python
import urllib.request
import json

req = urllib.request.Request(
    'http://127.0.0.1:5000/api/reminders',
    headers={'Authorization': f'Bearer {token}'}
)

with urllib.request.urlopen(req) as resp:
    data = json.loads(resp.read().decode())
    
    # 验证计算正确性
    for item in data[:20]:
        expected_days = item.get('total_quantity', 0) * 30
        actual_days = item.get('total_days', 0)
        if expected_days != actual_days:
            print(f"❌ {item['patient_name']}: 期望{expected_days}, 实际{actual_days}")
            
print("✓ 计算验证完成")
```

#### 清空 Python 缓存强制重载

```bash
#!/bin/bash
# reload-gunicorn.sh - 强制清理并重启

pkill -9 gunicorn
sleep 2

cd /path/to/backend

# 删除所有 Python 缓存
find . -name "*.pyc" -delete
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null

echo "✓ 清理完成"

# 启动新实例
/usr/local/bin/gunicorn --bind 127.0.0.1:5000 app:app
```

### 6. 模块化改进建议

#### JWT 认证独立化

```python
# ❌ 避免：从外部文件导入装饰器
from auth import auth_required  # 可能导致导入路径混乱

# ✅ 推荐：蓝图内自建轻量认证
from functools import wraps
from flask import request, g
import jwt

JWT_SECRET = 'your-secret-key'

def verify_token(token):
    """Verify and decode JWT token"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

def auth_required(f):
    """Decorator to require authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        token = auth_header.split(' ')[1] if auth_header and auth_header.startswith('Bearer ') else None
        
        if not token:
            return jsonify({"error": "缺少认证令牌"}), 401
        
        payload = verify_token(token)
        if not payload:
            return jsonify({"error": "无效或过期的令牌"}), 401
        
        g.user_id = payload['user_id']
        g.username = payload['username']
        g.roles = payload.get('roles', [])
        
        return f(*args, **kwargs)
    
    return decorated_function
```

#### 统一数据处理类

```python
class PatientDataProcessor:
    """患者数据计算服务类"""
    
    DAYS_PER_UNIT = 30  # 每两膏方服用天数
    
    @staticmethod
    def identify_patient(record, session):
        """
        四字段精确匹配患者
        
        Returns: List[PrescriptionRecord] sorted by pickup_date desc
        """
        from sqlalchemy import or_
        
        return session.query(PrescriptionRecord).filter(
            PrescriptionRecord.patient_name == record.patient_name,
            PrescriptionRecord.gender == record.gender,
            PrescriptionRecord.age == record.age,
            or_(
                PrescriptionRecord.patient_phone == (record.patient_phone or ""),
                (PrescriptionRecord.patient_phone.is_(None) & ((record.patient_phone or "") == ""))
            )
        ).order_by(PrescriptionRecord.pickup_date.desc()).all()
    
    @classmethod
    def calculate_window_total(cls, records, window_days=3):
        """计算时间窗口内的总量"""
        if not records:
            return 0
            
        latest_date = records[0].pickup_date.date()
        start_date = latest_date - timedelta(days=window_days)
        
        return sum(
            r.quantity or 0
            for r in records
            if r.pickup_date and start_date <= r.pickup_date.date() <= latest_date
        )
    
    @classmethod
    def calculate_days(cls, total_quantity):
        """计算服用天数"""
        return int(total_quantity) * cls.DAYS_PER_UNIT
```

## 故障排查清单

| 症状 | 可能原因 | 解决方法 |
|------|----------|----------|
| 计算结果总是 0 | 查询条件过严 | 检查匹配字段是否有 NULL |
| 修改代码不生效 | `.pyc` 缓存干扰 | 删除 cache 并重启 Gunicorn |
| 患者被误识别为他人 | 年龄/电话字段不一致 | 使用更稳定的标识符组合 |
| 前端显示 401 | Token 未传递或过期 | 检查 fetch header 中的 Authorization |
| SQL 报错类型不匹配 | 隐式转换失败 | 显式 cast 或统一类型 |
| 统计数据偏少 | 时间窗口计算有误 | 打印 start/end 日期验证 |

## 性能优化

### 避免 N+1 查询

```python
# ❌ 慢：循环内查询
for patient in patients:
    prescriptions = db.query(PrescriptionRecord).filter(name==patient.name).all()
    # ...

# ✅ 快：批量查询 + 内存分组
from collections import defaultdict

all_prescriptions = db.query(PrescriptionRecord).filter(
    PrescriptionRecord.patient_name.in_([p.name for p in patients])
).all()

prescriptions_by_patient = defaultdict(list)
for pres in all_prescriptions:
    key = f"{pres.patient_name}_{pres.gender}"
    prescriptions_by_patient[key].append(pres)
```

### 添加索引

```sql
-- 加速患者识别查询（复合索引）
CREATE INDEX idx_patient_lookup ON prescription_record (
    patient_name, gender, patient_phone
);

-- 加速时间范围查询
CREATE INDEX idx_pickup_date_desc ON prescription_record (pickup_date DESC);
```

## 验收标准

修复完成后应该能清晰回答：

- [ ] 患者识别的几个关键条件是什么？为什么选择这些字段？
- [ ] 时间窗口的准确定义（开始点和结束点）？
- [ ] 每个计量单位的换算系数是多少？
- [ ] 边缘情况（空值、首次取药、无记录）如何处理？
- [ ] 测试覆盖了哪些典型场景（单个、多个、跨天、边界）？

如果以上问题的答案清晰且有对应的测试验证，说明业务逻辑已正确实现。

## 实战案例：膏方管理系统总料数计算

### 问题演变

1. **第一次尝试**：累加患者所有历史处方
   ```python
   total = sum(p.quantity for p in all_patients_records)  # 错误！包含多年前的记录
   ```
   
2. **第二次调整**：按姓名 + 性别 + 年龄匹配
   ```python
   filter(age == record.age)  # 错误！年龄会从 73 变为 74
   ```
   
3. **最终方案**：四字段匹配 + 4 天窗口
   ```python
   # ✓ 正确：姓名 + 性别 + 年龄 + 电话 + 短期窗口
   or_(phone == filter_phone, (phone.is_(None) & (filter_phone == "")))
   start_date = latest_date - timedelta(days=3)
   total = sum(qty for recs where start_date <= pickup_date <= latest_date)
   ```

### 验证结果

```
患者：毕重敏
- 历史记录：9 次取药，共 11 两
- 但最近 4 天内：仅 3 两（其他记录太早）
- 总服用天数：3 × 30 = 90 天 ✓
```

---

## 扩展：患者累计统计的完整方法论

以下内容整合自 `flask-patient-cumulative-calculation` 和 `flask-sqlalchemy-cumulative-aggregation`。

### 患者识别的多维度精确匹配

**❌ 错误做法:** 只用姓名或加年龄（年龄会从 73 变 74，导致漏计）

**✅ 正确做法:** 四维匹配（姓名 + 性别 + 年龄 + 电话）

```python
all_prescriptions_raw = db.query(PrescriptionRecord).filter(
    PrescriptionRecord.patient_name == record.patient_name,
    PrescriptionRecord.gender == record.gender,
    PrescriptionRecord.age == record.age
).order_by(PrescriptionRecord.pickup_date.desc()).all()

# Python 层精确过滤电话号码（处理 NULL）
phone_filter = record.patient_phone or ""
all_prescriptions = [
    p for p in all_prescriptions_raw
    if (p.patient_phone or "") == phone_filter
]
```

### 时间窗口计算

```python
from datetime import timedelta, date

if len(all_prescriptions) > 0:
    latest_record = all_prescriptions[0]
    latest_pickup_date = latest_record.pickup_date

    if latest_pickup_date:
        latest_date_obj = (latest_pickup_date.date()
                          if hasattr(latest_pickup_date, 'date')
                          else latest_pickup_date)

        start_date_3days = latest_date_obj - timedelta(days=3)

        total_quantity = sum(
            p.quantity or 0
            for p in all_prescriptions
            if p.pickup_date and (start_date_3days <= p.pickup_date.date() <= latest_date_obj)
        )
    else:
        total_quantity = record.quantity or 0
else:
    total_quantity = record.quantity or 0

total_days = total_quantity * 30  # 每两膏方服用 30 天
```

### 性能优化：避免 N+1 查询

```python
from collections import defaultdict

# ✅ 批量查询 + 内存分组
all_prescriptions = db.query(PrescriptionRecord).filter(
    PrescriptionRecord.patient_name.in_([p.name for p in patients])
).all()

prescriptions_by_patient = defaultdict(list)
for pres in all_prescriptions:
    key = f"{pres.patient_name}_{pres.gender}"
    prescriptions_by_patient[key].append(pres)
```

### 推荐匹配策略

| 方案 | 准确率 | 推荐度 |
|------|--------|--------|
| user_id 外键 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐（如能改造 DB） |
| name + gender + age + phone | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| name + gender + age | ⭐⭐⭐ | ⭐⭐⭐ |
| only name | ⭐ | ❌ |

### 关键教训

- 年龄会随时间变化，不能作为唯一长期标识
- 电话号码相对稳定，是很好的辅助字段
- 先确认业务规则（时间窗口、换算系数）再编码
- 空值处理：统一用 `(value or "")` 模式