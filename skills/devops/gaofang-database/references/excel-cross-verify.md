# Excel 数据交叉验证

当用户发来导入Excel文件要求验证数据库数据时使用。

## 场景

用户说"我统计的是X，你查出来是Y，不对" → 发来Excel文件 → 需要找出差异原因。

## 常见差异原因

1. **时间口径不同** — 用户按Excel文件本身算，数据库按 created_at 可能包含多次导入
2. **手动录入** — 数据库中有非Excel导入的手动添加记录
3. **数据删除** — 用户调整后删除了部分记录

## 验证步骤

### 1. 读取Excel

```python
import openpyxl
wb = openpyxl.load_workbook('文件路径.xlsx')
ws = wb.active

total_liao = 0
excel_ids = set()
for row in ws.iter_rows(min_row=2, max_row=ws.max_row, values_only=True):
    pid = str(row[2]).strip() if row[2] else ''     # 处方编号在第3列(索引2)
    liao = int(row[9]) if row[9] and str(row[9]).isdigit() else 0  # 料数在第10列(索引9)
    total_liao += liao
    if pid:
        excel_ids.add(pid)

print(f'Excel料数合计: {total_liao}')
```

注意：Excel列映射根据导出模板变化。标准「代煎导出」格式中：
- 列3(索引2) = 处方编号
- 列10(索引9) = 料数

### 2. 对比数据库

```sql
-- 找出 DB 有但 Excel 无的记录
SELECT id, prescription_id, patient_name, date, quantity, status, created_at
FROM prescription_records
WHERE created_at >= '目标月份1号' AND created_at < '下个月1号'
  AND prescription_id NOT IN ('Excel中的ID列表');
```

### 3. 向用户报告

格式：Excel有X条/Y料，DB多出N条/M料，如下：

| 患者 | 处方编号 | 料数 |
|:----|:--------:|:---:|
| XXX | 编号 | N料 |
| 合计 | | M料 |

> 不要争论数据谁对谁错 — 只陈述差异事实，让用户确认。
