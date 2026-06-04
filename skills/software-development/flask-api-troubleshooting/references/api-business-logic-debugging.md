# Flask API 业务逻辑调试方法论

> 吸收自 `flask-api-business-logic-debugging`（2026-05 合并）
> 本节涵盖实现累计计算、时间窗口统计、患者识别等复杂业务场景的系统方法。

## 患者识别最佳实践

### 年龄会随时间变化！

```python
# ❌ 错误：使用固定年龄匹配会导致漏计
db.query(User).filter(User.age == age)

# ✅ 正确：考虑年龄变化的匹配策略
db.query(User).filter(
    User.patient_name == name,
    User.gender == gender,
    User.phone == phone  # 最可靠的标识符
)
```

### 推荐匹配策略

| 策略 | 优点 | 适用场景 |
|------|------|----------|
| 姓名 + 性别 + 电话 | 精确稳定 | **生产环境首选** |
| 姓名 + 性别 | 简单 | 小型诊所 (<500 人) |
| 唯一 ID（UUID） | 完美 | 新项目设计 |
| 四字段全匹配（含年龄） | ⚠️ 谨慎使用 | 年龄变化导致漏计 |

## 时间窗口统计实现

```python
from datetime import date, timedelta

def calculate_window_total(records, window_days=3):
    """计算时间窗口内的总量"""
    if not records:
        return 0
    latest_date = records[0].pickup_date.date()
    start_date = latest_date - timedelta(days=window_days)
    return sum(
        r.quantity or 0 for r in records
        if r.pickup_date and start_date <= r.pickup_date.date() <= latest_date
    )
```

## 故障排查清单

| 症状 | 可能原因 | 解决方法 |
|------|----------|----------|
| 计算结果总是 0 | 查询条件过严 | 检查匹配字段是否有 NULL |
| 修改代码不生效 | `.pyc` 缓存干扰 | 删除 cache 并重启 Gunicorn |
| 患者被误识别 | 年龄/电话字段不一致 | 使用更稳定的标识符组合 |
| 统计数据偏少 | 时间窗口计算有误 | 打印 start/end 日期验证 |

## 性能优化

### 避免 N+1 查询

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

### 数据库索引

```sql
CREATE INDEX idx_patient_lookup ON prescription_record (patient_name, gender, patient_phone);
CREATE INDEX idx_pickup_date_desc ON prescription_record (pickup_date DESC);
```
