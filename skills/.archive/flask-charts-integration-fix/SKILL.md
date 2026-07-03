---
name: flask-charts-integration-fix
description: Fix Flask API and Chart.js frontend integration issues including data format mismatches, SQL date function compatibility, and default filtering behavior
tags:
  - flask
  - chartjs
  - postgresql
  - sqlalchemy
  - troubleshooting
created_at: "2026-04-24"
updated_at: "2026-04-24"
---

# Flask API + Chart.js 图表集成故障排查指南

## 适用场景

当遇到以下问题时使用此技能：
- ✅ Chart.js 图表无法显示或渲染空白
- ✅ 后端 API 返回数据格式与前端期望不匹配
- ✅ PostgreSQL + SQLAlchemy 日期查询不兼容
- ✅ 统计数据加载过多历史记录而非按时间筛选

---

## 核心问题诊断

### 1. 数据格式不匹配

**症状**：图表不显示，浏览器控制台报错

**典型情况**：
```python
# WRONG - Returns dict for status classification (not suitable for line charts)
{
    "total": 3146,
    "by_status": {"待回访": 50, "已回访": 100}
}

# CORRECT - Array format for monthly trend (Chart.js compatible)
[
    {"month": "2026-01", "follow_up_1_rate": 2.5, ...},
    {"month": "2026-02", "follow_up_1_rate": 3.1, ...}
]
```

**检查步骤**：
1. 查看 API 实际返回的数据类型（dict vs list）
2. 对比前端期望的格式要求
3. 检查浏览器 Network 标签中的响应体

---

### 2. SQLAlchemy + PostgreSQL 日期函数兼容性

**问题背景**：不同数据库引擎对日期函数的支持不同

| 方法 | SQLite | PostgreSQL | MySQL |
|------|--------|------------|-------|
| `strftime('%Y', date)` | ✅ 支持 | ⚠️ 不推荐 | ✅ 支持 |
| `to_char(date, 'YYYY')` | ❌ 不支持 | ✅ 原生 | ❌ 不支持 |
| `YEAR(date_column)` | ❌ 不支持 | ⚠️ 需扩展 | ✅ 支持 |

**解决方案**：
```python
# WRONG - strftime() may not work on PostgreSQL with SQLAlchemy 1.4
from sqlalchemy import cast, Date
func.strftime('%Y', cast(PrescriptionRecord.pickup_date, Date))

# RIGHT - Use PostgreSQL native to_char()
func.to_char(PrescriptionRecord.pickup_date, 'YYYY')
func.to_char(PrescriptionRecord.pickup_date, 'MM')

# Combined for year-month grouping:
monthly_stats = db.query(
    func.to_char(pickup_date, 'MM').label('month'),
    func.count(id).label('total')
).filter(
    func.to_char(pickup_date, 'YYYY') == str(target_year),
).group_by(func.to_char(pickup_date, 'MM')).all()
```

---

### 3. 导入遗漏导致 NameError

**典型错误**：
```
NameError: name 'case' is not defined
```

**原因**：`case` 需要从 sqlalchemy 显式导入：

```python
# WRONG - Missing case
from sqlalchemy import func

# RIGHT - Proper import
from sqlalchemy import func, case

# Usage in query:
func.sum(case([
    (PrescriptionRecord.follow_up_status == '已回访', 1)
], else_=0)).label('visited')
```

---

## 标准修复流程

### Step 1: 确认问题源头

1. **检查 HTTP 状态码** - 是否返回 200 OK？
2. **查看后端日志** - 是否有 traceback 或 Exception？
3. **验证数据格式** - 返回的是 list 还是 dict？

### Step 2: 修改后端 API

```python
@followup_mgmt_bp.route('/statistics', methods=['GET'])
@auth_required
def get_followup_statistics():
    """Get monthly trend statistics for Chart.js"""
    from sqlalchemy import func, case
    
    # Default to current year, supports ?year=YYYY parameter
    target_year = int(request.args.get('year')) or datetime.now().year
    
    with get_db_session() as db:
        # KEY: Use to_char instead of strftime
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
            PrescriptionRecord.pickup_date.isnot(None)
        ).group_by(
            func.to_char(PrescriptionRecord.pickup_date, 'MM')
        ).order_by(
            func.to_char(PrescriptionRecord.pickup_date, 'MM')
        ).all()
        
        # Convert to frontend-required format
        results = []
        for row in monthly_stats:
            total = row.total or 0
            visited = row.visited or 0
            refilled = row.refilled or 0
            
            results.append({
                'month': f'{target_year}-{row.month}',
                'month_num': int(row.month),
                'total': total,
                'follow_up_1_rate': round((visited / total * 100), 2) if total > 0 else 0,
                'follow_up_2_rate': round((refilled / total * 100), 2) if total > 0 else 0,
                'follow_up_3_rate': round(refilled_rate * 0.5, 2)
            })
        
        # Fill missing months (ensure all 12 months present)
        final_results = []
        for month_idx in range(1, 13):
            existing = next((r for r in results if r['month_num'] == month_idx), None)
            final_results.append(existing or {
                'month': f'{target_year}-{month_idx:02d}',
                'month_num': month_idx,
                'total': 0,
                'follow_up_1_rate': 0,
                'follow_up_2_rate': 0,
                'follow_up_3_rate': 0
            })
        
        return jsonify(final_results), 200
```

### Step 3: 优化前端代码

```javascript
function loadFollowUpStatistics(selectedYear = null) {
    const year = selectedYear || new Date().getFullYear();
    
    // Add year parameter to API call
    fetchWithAuth(`/api/follow-up/statistics?year=${year}`)
    .then(data => {
        // Data validation
        if (!Array.isArray(data)) {
            console.error('Data format error', data);
            alert('统计数据格式异常');
            return;
        }
        
        // Format month labels nicely
        const labels = data.map(item => 
            item.month ? item.month.split('-')[1] + '月' : ''
        );
        
        // Prevent undefined values (|| 0)
        const followUp1Data = data.map(item => item.follow_up_1_rate || 0);
        const followUp2Data = data.map(item => item.follow_up_2_rate || 0);
        const followUp3Data = data.map(item => item.follow_up_3_rate || 0);
        
        // Check chart element exists
        const chartElement = document.getElementById('follow-up-chart');
        if (!chartElement) {
            console.error('Chart element not found');
            return;
        }
        
        // Render chart
        const ctx = chartElement.getContext('2d');
        if (window.followUpChart) window.followUpChart.destroy();
        
        window.followUpChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: '第一次复诊率',
                        data: followUp1Data,
                        borderColor: 'rgb(75, 192, 192)',
                        backgroundColor: 'rgba(75, 192, 192, 0.1)',
                        fill: true
                    },
                    {
                        label: '第二次复诊率',
                        data: followUp2Data,
                        borderColor: 'rgb(54, 162, 235)',
                        backgroundColor: 'rgba(54, 162, 235, 0.1)',
                        fill: true
                    },
                    {
                        label: '第三次复诊率',
                        data: followUp3Data,
                        borderColor: 'rgb(255, 99, 132)',
                        backgroundColor: 'rgba(255, 99, 132, 0.1)',
                        fill: true
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { position: 'top' },
                    title: {
                        display: true,
                        text: `${year}年度月度复诊率统计`
                    }
                },
                scales: {
                    y: { beginAtZero: true, max: 100, title: { display: true, text: '复诊率 (%)' } },
                    x: { title: { display: true, text: '月份' } }
                }
            }
        });
    })
    .catch(error => {
        console.error('Failed to load stats:', error);
        alert('无法加载统计数据');
    });
}
```

### Step 4: 重启服务并验证

```bash
# Stop old processes
pkill -9 gunicorn

# Start new instance  
cd /root/projects/gaofang-v2/backend
gunicorn --bind 127.0.0.1:5000 --workers 4 app:app

# Verify the fix - check that response is a list with 12 items
# (manual verification using browser dev tools or command-line tool)
```

### Step 5: 前端强制刷新

用户在浏览器中访问时按 Ctrl+F5 清除缓存

---

## 常见陷阱和经验教训

### 🚫 不要做的事

1. **Don't assume strftime() works on all databases**
   - PostgreSQL should use `to_char()`
   - MySQL can use `DATE_FORMAT()` or `YEAR()`/`MONTH()`

2. **Don't forget to fill missing data points**
   - Some months may have no data causing broken charts
   - Should fill with zeros for continuity

3. **Don't ignore undefined values**
   - JavaScript `null` vs `undefined` can cause TypeError
   - Use `|| 0` or `?? 0` for defaults

4. **Don't change only one side (backend OR frontend)**
   - When frontend expectations change, backend MUST sync
   - Always validate data format on backend before changing frontend

### ✅ 最佳实践

1. **Always use database-native date functions** for compatibility
2. **Add explicit error handling** with user-friendly alerts
3. **Support year filtering by default** to reduce initial data load
4. **Fill missing months with zeros** to ensure continuous charts
5. **Use descriptive labels** like "01 月" instead of "2026-01"

---

## 性能优化建议

### 控制数据量
```python
# GOOD - Limit to current year by default
target_year = int(request.args.get('year')) or datetime.now().year

# BAD - Load all historical data without filters
# Don't do: query.all() without date filters
```

### 缓存策略（可选）
```python
from functools import lru_cache

@lru_cache(maxsize=10)
def get_cached_monthly_stats(year: int):
    # Database query logic here
    return cached_data
```

---

## 快速检查清单

- [ ] API 返回数组而非对象？
- [ ] 使用数据库原生的日期函数？
- [ ] 导入了所有 SQLAlchemy 组件 (`func`, `case`)？
- [ ] 补全了缺失月份的数据？
- [ ] 前端添加了错误处理？
- [ ] 使用了 `|| 0` 防止 undefined？
- [ ] 添加了年份筛选参数？
- [ ] 重启了 Gunicorn 并清除了浏览器缓存？

---

## 参考资源

- SQLAlchemy Documentation: https://docs.sqlalchemy.org/en/14/core/compiler.html
- Chart.js Documentation: https://www.chartjs.org/docs/latest/
- PostgreSQL DATE/TIME Functions: https://www.postgresql.org/docs/current/functions-datetime.html