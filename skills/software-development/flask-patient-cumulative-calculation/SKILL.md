---
title: "[ARCHIVED] Flask SQLAlchemy 患者累计统计计算最佳实践"
description: "[已合并到 flask-api-business-logic-debugging] 医疗管理系统中计算患者累计数据的方法论，包含精确识别和窗口过滤"
name: flask-patient-cumulative-calculation
tags:
  - archived
  - flask
  - sqlalchemy
  - patient-data
  - cumulative-calculation
version: 1.0
author: Hermes Agent
date_created: 2026-04-24
related_skills:
  - sqlite-to-postgresql-migration
  - flask-api-troubleshooting
---

# Flask SQLAlchemy 患者累计统计计算最佳实践

在医疗管理系统中计算患者的累计数据（如总处方量、服用天数等）时，需要注意患者识别准确性和业务规则的时间窗口限制。

## 典型场景

膏方管理系统中的「服用周期提醒」功能，需要显示：
1. 患者身份识别
2. 总料数（近期取药总量）
3. 总服用天数（基于总料数计算）

## 核心要点

### 1. 患者识别必须多维度精确匹配

❌ **错误做法** - 只用姓名或加年龄：
```python
# 年龄会随时间变化，73 岁变 74 岁的记录会被遗漏
all_prescriptions = db.query(PrescriptionRecord).filter(
    PrescriptionRecord.patient_name == record.patient_name,
    PrescriptionRecord.gender == record.gender
).all()
```

✅ **正确做法** - 四维匹配（姓名 + 性别 + 年龄 + 电话）：
```python
all_prescriptions_raw = db.query(PrescriptionRecord).filter(
    PrescriptionRecord.patient_name == record.patient_name,
    PrescriptionRecord.gender == record.gender,
    PrescriptionRecord.age == record.age
).order_by(PrescriptionRecord.pickup_date.desc()).all()

# 手动过滤电话号码（Python 层面更灵活处理 NULL）
phone_filter = record.patient_phone or ""
all_prescriptions = [
    p for p in all_prescriptions_raw 
    if (p.patient_phone or "") == phone_filter
]
```

### 2. 使用合理的时间窗口

**问题**：累加患者历史所有处方可能导致不合理数值（如多年前的旧记录也被计入）。

**解决方案**：限定时间窗口，通常使用"最后取药日及前 N 日内"的逻辑：

```python
from datetime import timedelta, date

if len(all_prescriptions) > 0:
    latest_record = all_prescriptions[0]
    latest_pickup_date = latest_record.pickup_date
    
    if latest_pickup_date:
        # 标准化日期对象
        latest_date_obj = (latest_pickup_date.date() 
                          if hasattr(latest_pickup_date, 'date') 
                          else latest_pickup_date)
        
        # 计算起始日期（最后取药日前推 3 天）
        start_date_3days = latest_date_obj - timedelta(days=3)
        
        # 只累加时间窗口内的处方量
        total_quantity = sum(
            p.quantity or 0
            for p in all_prescriptions
            if p.pickup_date and (start_date_3days <= p.pickup_date.date() <= latest_date_obj)
        )
    else:
        total_quantity = record.quantity or 0
else:
    total_quantity = record.quantity or 0
```

### 3. 业务规则的公式应用

膏方按标准剂量计算服用天数：
```python
total_days = total_quantity * 30  # 每两膏方服用 30 天
```

## 完整示例

```python
def get_reminders():
    """获取需提醒的患者，附带准确的累计统计"""
    
    with get_db_session() as db:
        query = db.query(PrescriptionRecord).filter(...)
        results = query.all()
        
        patients_list = []
        
        for record in results:
            # ... 判断是否需要提醒的逻辑 ...
            
            if not reminder_type:
                continue
            
            # === 累计计算开始 ===
            all_prescriptions_raw = db.query(PrescriptionRecord).filter(
                PrescriptionRecord.patient_name == record.patient_name,
                PrescriptionRecord.gender == record.gender,
                PrescriptionRecord.age == record.age
            ).order_by(PrescriptionRecord.pickup_date.desc()).all()
            
            phone_filter = record.patient_phone or ""
            all_prescriptions = [
                p for p in all_prescriptions_raw 
                if (p.patient_phone or "") == phone_filter
            ]
            
            if len(all_prescriptions) > 0:
                latest_date_obj = all_prescriptions[0].pickup_date.date()
                start_date_3days = latest_date_obj - timedelta(days=3)
                
                total_quantity = sum(
                    p.quantity or 0
                    for p in all_prescriptions
                    if p.pickup_date and (start_date_3days <= p.pickup_date.date() <= latest_date_obj)
                )
            else:
                total_quantity = record.quantity or 0
            
            total_days = total_quantity * 30
            # === 累计计算结束 ===
            
            patient_data = {
                'quantity': record.quantity,           # 本次处方
                'total_quantity': total_quantity,      # 近期累计
                'total_days': total_days               # 服用天数
            }
            patients_list.append(patient_data)
        
        return jsonify(patients_list), 200
```

## 常见陷阱与调试经验

### 陷阱 1: Python `.pyc` 缓存导致代码未更新

**症状**: 修改了代码但 Gunicorn 仍在返回旧逻辑的结果

**解决**:
```bash
find . -name "*.pyc" -delete && find . -type d -name "__pycache__" -exec rm -rf {} +
pkill -9 gunicorn && cd /path/to/backend && gunicorn --bind 127.0.0.1:5000 app:app
```

### 陷阱 2: 年龄字段导致漏计

**第一次尝试**：只用姓名 + 性别 → 无法区分同名同性患者  
**第二次尝试**：加年龄字段 → 发现毕重敏年龄从 73 变 74 导致漏计部分记录  
**最终方案**：加电话号码作为第四维度 → 准确唯一识别

### 陷阱 3: SQL 逻辑运算符优先级

```python
# ❌ SQLAlchemy | 和 & 容易出错
PrescriptionRecord.patient_phone == phone_filter | \
    (PrescriptionRecord.patient_phone.is_(None) & (phone_filter == ""))

# ✅ 推荐：先用基础条件查询，Python 列表推导式过滤
raw_records = db.query(...).filter(基本条件).all()
filtered = [r for r in raw_records if condition(r)]
```

### 陷阱 4: NULL 值比较

```python
# ❌ NULL != "" 直接比较会出问题
if record.phone == other.phone:

# ✅ 统一转换为空字符串
if (record.phone or "") == (other.phone or ""):
```

## 验证方法

测试时检查：
- 同名不同号的人不被混淆
- 时间窗口外的处方不计入
- `total_days == total_quantity * 30`

```python
for item in data:
    assert item['total_days'] == item['total_quantity'] * 30
```

## 适用场景扩展

此模式适用于：
- 医疗系统的用药周期管理
- 电商平台的近期消费总额统计
- 教育系统的课时累计追踪
- 任何需要"近期窗口内累计统计"的业务场景

## 实战案例回顾

**项目**: 膏方管理系统 V2 服用周期提醒功能  
**迭代过程**:
1. 第一轮：累加所有历史处方 → 毕重敏显示 11 两
2. 第二轮：移除年龄限制 → 仍显示不正确
3. 第三轮：理解业务需求 → "最近 4 天内累计"而非"全部历史"
4. 最终实现：四字段匹配 + 3 天窗口 → 毕重敏显示 3 两 ✓

**关键教训**: 业务需求理解优先于技术方案设计，先明确"什么是合理的总计"再编码。