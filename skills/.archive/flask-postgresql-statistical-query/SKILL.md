---
name: flask-postgresql-statistical-query
description: Flask + SQLAlchemy + PostgreSQL 统计查询与日期处理最佳实践
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [flask, postgresql, sqlalchemy, statistics, date-functions]
    related_skills: [flask-api-troubleshooting, sqlite-to-postgresql-migration-with-sqlalchemy]
---

# Flask + PostgreSQL 统计查询与日期处理指南

## Overview

本技能提供 Flask + SQLAlchemy + PostgreSQL 组合下进行统计分析时的常见问题和解决方案，特别适用于月度/年度趋势图表的数据查询场景。

**核心价值**: 避免日期函数兼容性陷阱，提供稳定的统计查询模式

---

## When to Use

**适用场景:**
- Flask Web 应用使用 SQLAlchemy ORM 操作 PostgreSQL
- 需要按时间维度（月/年/季度）分组统计数据
- 前端使用 Chart.js、ECharts 等库展示趋势图
- Python 3.6+ 环境配合 SQLAlchemy 1.4.x

**典型错误信号:**
- `NameError: name 'case' is not defined`
- SQLAlchemy 查询报错或返回空数据
- SQL 语法错误提示不支持某些函数

---

## Core Solutions

### Issue 1: PostgreSQL 日期函数选择

#### ❌ 错误写法（不推荐）

```python
from sqlalchemy import func, cast, Date

monthly_stats = db.query(
    func.strftime('%m', cast(column, Date)).label('month'),
).filter(
    func.strftime('%Y', cast(PrescriptionRecord.pickup_date, Date)) == str(year),
)
```

**问题**:
- `strftime()` + `cast()` 依赖 SQLAlchemy 的类型推断层
- 在 Python 3.6 + SQLAlchemy 1.4.x 环境中可能失败
- 不同数据库后端的行为不一致

#### ✅ 正确写法（PostgreSQL 原生函数）

```python
from sqlalchemy import func

monthly_stats = db.query(
    func.to_char(PrescriptionRecord.pickup_date, 'MM').label('month'),
    func.count(PrescriptionRecord.id).label('total'),
).filter(
    func.to_char(PrescriptionRecord.pickup_date, 'YYYY') == str(target_year),
)
```

**优势**:
- `to_char()` 直接映射到 PostgreSQL 同名函数
- 绕过中间层的类型推断，更稳定
- 在旧版 Python 环境中兼容性更好

**PostgreSQL to_char() 格式代码:**
- `'YYYY'`: 四位年份 (2026)
- `'YY'`: 两位年份 (26)
- `'MM'`: 月份 (01-12)
- `'DD'`: 日期 (01-31)

---

### Issue 2: Case When 语法兼容性（Python 3.6 + SQLAlchemy 1.4）

#### ❌ 错误写法1：导入遗漏

```python
# NameError: name 'case' is not defined
func.sum(case(...))
```

#### ❌ 错误写法2：新语法在旧版上崩溃

SQLAlchemy 1.4 引入了 **位置参数语法** `case((cond, value), else_=0)`，但这在 Python 3.6 + SQLAlchemy 1.4.x 环境中会报：

```
Operator 'getitem' is not supported on this expression
```

```python
# ❌ Python 3.6 + SQLAlchemy 1.4 上会崩溃
case(
    (PrescriptionRecord.follow_up_1_status == '已复诊', 1),
    else_=0
)
```

#### ✅ 正确写法：使用 SQL 原生语句（最可靠）

当 ORM 的特定语法在旧版 Python 上不兼容时，**直接使用原生 SQL 是最简单的解决方案**：

```python
@followup_mgmt_bp.route('/follow-up/statistics', methods=['GET'])
def get_follow_up_statistics():
    session = db.session
    try:
        sql = """
            SELECT
                to_char(pickup_date, 'YYYY-MM') AS month,
                COUNT(id) AS total_patients,
                SUM(CASE WHEN follow_up_1_status = '已复诊' THEN 1 ELSE 0 END) AS follow_up_1_count,
                SUM(CASE WHEN follow_up_2_status = '已复诊' THEN 1 ELSE 0 END) AS follow_up_2_count,
                SUM(CASE WHEN follow_up_3_status = '已复诊' THEN 1 ELSE 0 END) AS follow_up_3_count
            FROM prescription_records
            WHERE status = '已取' AND pickup_date IS NOT NULL
            GROUP BY month
            ORDER BY month
        """
        results = session.execute(sql).fetchall()

        result = []
        for row in results:
            month_data = {
                'month': row[0],
                'total_patients': int(row[1]) if row[1] else 0,
                'follow_up_1_count': int(row[2]) if row[2] else 0,
                'follow_up_2_count': int(row[3]) if row[3] else 0,
                'follow_up_3_count': int(row[4]) if row[4] else 0,
            }
            # 计算百分比...
            result.append(month_data)

        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
```

**注意**：`session.execute(sql)` 返回的 `ResultProxy` 行通过 **数字索引** `row[0]`, `row[1]` 访问列，不是通过属性名。

#### ✅ 正确写法（ORM 方式，使用列表语法 `case([...], else_=0)`）

如果坚持用 ORM，**必须用列表式语法** `case([(cond, value)], else_=0)`，这是 SQLAlchemy 1.4 仍支持的旧语法：

```python
from sqlalchemy import func, case

monthly_stats = db.query(
    func.to_char(PrescriptionRecord.pickup_date, 'MM').label('month'),
    func.count(PrescriptionRecord.id).label('total'),
    func.sum(case([
        (status_column == '已回访', 1)
    ], else_=0)).label('visited_count'),
).group_by(func.to_char(PrescriptionRecord.pickup_date, 'MM')).all()
```

⚠️ **注意**：`group_by('month')` **使用字符串引用列别名在旧版 SQLAlchemy 上不可靠**。必须直接用完整表达式 `group_by(func.to_char(...))` 而不是字符串 `group_by('month')`。

**关键点**:
- `case` 必须显式从 sqlalchemy 导入
- Python 3.6 上使用 `case([(cond, val)], else_=0)` 列表语法，不要用 `case((cond, val), else_=0)` 位置参数语法
- `group_by()` 和 `order_by()` 不要传字符串，传完整 SQLAlchemy 表达式
- 如果同时遇到多个兼容性问题，**直接改用原生 SQL** 是最快路径

#### 常见错误

```
NameError: name 'case' is not defined
```

#### 正确做法

```python
from sqlalchemy import func, case

# 条件计数示例
monthly_stats = db.query(
    func.to_char(date_column, 'MM').label('month'),
    func.sum(case([
        (status_column == '已回访', 1)
    ], else_=0)).label('visited_count'),
    func.sum(case([
        (status_column == '已复诊', 1)
    ], else_=0)).label('repurchase_count'),
).group_by(func.to_char(date_column, 'MM')).all()
```

**关键点**: `case` 必须显式从 sqlalchemy 导入

---

### Issue 3: 聚合函数正确使用

#### ❌ 错误用法

```python
# label() 不是聚合函数！
func.sum(column.label('count'))  # 会报错
```

#### ✅ 正确用法

```python
from sqlalchemy import func

# 先聚合，再命名
func.count(PrescriptionRecord.id).label('total')
func.sum(amount_column).label('total_amount')
func.avg(rating_column).label('avg_rating')
```

**常用聚合函数:**
- `func.count(column)`: 计数
- `func.sum(column)`: 求和
- `func.avg(column)`: 平均值
- `func.max(column)`: 最大值
- `func.min(column)`: 最小值
- `func.array_agg(column)`: 数组聚合（PostgreSQL 特有）

---

## Complete Template: Monthly Statistics API

```python
@followup_mgmt_bp.route('/statistics', methods=['GET'])
@auth_required
def get_followup_statistics():
    """获取月度复诊率统计"""
    from sqlalchemy import func, case
    
    # 支持年份参数，默认为当前年
    year_param = request.args.get('year')
    target_year = int(year_param) if year_param else datetime.now().year
    
    with get_db_session() as db:
        monthly_stats = db.query(
            func.to_char(PrescriptionRecord.pickup_date, 'MM').label('month'),
            func.count(PrescriptionRecord.id).label('total'),
            func.sum(case([
                (PrescriptionRecord.follow_up_status == '已回访', 1)
            ], else_=0)).label('visited'),
            func.sum(case([
                (PrescriptionRecord.follow_up_status == '已复诊', 1)
            ], else_=0)).label('refilled'),
        ).filter(
            func.to_char(PrescriptionRecord.pickup_date, 'YYYY') == str(target_year),
            PrescriptionRecord.status == '已取',
            PrescriptionRecord.pickup_date.isnot(None)  # 排除 null 日期
        ).group_by(
            func.to_char(PrescriptionRecord.pickup_date, 'MM')
        ).order_by(
            func.to_char(PrescriptionRecord.pickup_date, 'MM')
        ).all()
        
        # 转换为图表所需格式
        results = []
        for row in monthly_stats:
            month_num = int(row.month)
            total = row.total or 0
            visited = row.visited or 0
            refilled = row.refilled or 0
            
            results.append({
                'month': f'{target_year}-{row.month}',
                'month_num': month_num,
                'total': total,
                'visited_count': visited,
                'refilled_count': refilled,
                'follow_up_1_rate': round((visited / total * 100), 2) if total > 0 else 0,
                'follow_up_2_rate': round((refilled / total * 100), 2) if total > 0 else 0,
            })
        
        # 补全缺失月份（重要！保证 12 个月完整显示）
        final_results = []
        for month_idx in range(1, 13):
            existing = next((r for r in results if r['month_num'] == month_idx), None)
            
            if existing:
                final_results.append(existing)
            else:
                final_results.append({
                    'month': f'{target_year}-{month_idx:02d}',
                    'month_num': month_idx,
                    'total': 0,
                    'visited_count': 0,
                    'refilled_count': 0,
                    'follow_up_1_rate': 0,
                    'follow_up_2_rate': 0,
                })
        
        return jsonify(final_results), 200
```

---

## Common Pitfalls

| 现象 | 原因 | 解决方案 |
|------|------|----------|
| `NameError: case` | 缺少导入 | `from sqlalchemy import func, case` |
| SQL 语法错误 | 使用了 SQLite 的 strftime() | 改用 `to_char()` |
| 图表无数据 | 月份为 null 未过滤 | 添加 `.isnot(None)` 条件 |
| 数据不完整 | 某月无记录未填充 | 补全循环确保 12 个月都有数据 |
| 500 Internal Error | 除零错误或未捕获异常 | 添加 `if total > 0` 检查 |

---

## Performance Optimization

### 1. 索引优化

```sql
-- 复合索引覆盖常用查询
CREATE INDEX idx_records_status_date 
ON prescription_records(status, pickup_date);

-- 如果需要频繁按 follow_up_status 分组
CREATE INDEX idx_records_status_followup_date 
ON prescription_records(follow_up_status, pickup_date);
```

### 2. 缓存策略

```python
from flask_caching import Cache

cache = Cache(config={'CACHE_TYPE': 'redis'})

@cache.cached(timeout=3600, prefix='stats:followup')
def get_monthly_statistics(year):
    # ... 查询逻辑 ...
    pass
```

### 3. 避免全量加载

```python
# ❌ 不好：一次加载所有历史数据
all_stats = get_all_history_data()  # 几百万行

# ✅ 好：默认当年，按需查询
year = request.args.get('year', str(datetime.now().year))
stats = get_yearly_data(year)  # 仅 12 个月
```

---

## Testing Utilities

### Python API 测试脚本

```python
import json
import urllib.request

def test_api():
    # Login
    login_data = json.dumps({"username": "admin", "password": "123456"}).encode()
    req = urllib.request.Request(
        'http://127.0.0.1:5000/api/auth/login',
        data=login_data,
        headers={'Content-Type': 'application/json'}
    )
    with urllib.request.urlopen(req) as resp:
        token = json.loads(resp.read())['token']
    
    # Test statistics endpoint
    req = urllib.request.Request(
        'http://127.0.0.1:5000/api/follow-up/statistics?year=2026',
        headers={'Authorization': f'Bearer {token}'}
    )
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read())
        print(f"✓ Returned {len(data)} months")
        total_records = sum(d.get('total', 0) for d in data)
        print(f"✓ Total records: {total_records}")

if __name__ == '__main__':
    test_api()
```

### View Gunicorn Error Logs

```bash
# Real-time monitoring
tail -f /var/log/gaofang_error.log.gunicorn

# Find specific errors
grep -A5 "/api/follow-up/statistics" /var/log/gaofang_error.log.gunicorn
```

---

## Quick Checklist

- [ ] 使用 `to_char()` 而非 `strftime()` + `cast()`
- [ ] 导入了 `case` (如果用到条件表达式)
- [ ] 添加了 `isnot(None)` 过滤空日期
- [ ] 补全了所有月份（防止图表中断）
- [ ] 除以总数前检查是否大于 0
- [ ] 重启 Gunicorn 加载新代码
- [ ] 清除浏览器缓存 (Ctrl+F5)

---

## Related Skills

- `flask-api-troubleshooting`: Flask API 通用故障排查
- `sqlite-to-postgresql-migration-with-sqlalchemy`: SQLite 迁移到 PostgreSQL 的完整工作流
- `legacy-system-safe-refactoring`: 遗留系统安全重构方法论

---

*最后更新：2026-05-01*  
*项目背景：膏方管理系统 V2 升级 - 统计分析模块修复*
