# 导入规则变更记录

## 2026-07-15 新增：支付状态=定金跳过

### 背景

用户要求导入时如果某条记录的「支付状态」为"定金"，则跳过该条不导入。

### 代码变更

文件：`/workspace/projects/drug-distribution-system/gaofang-v2/import_template.py`

位置：`main()` 函数中，在必填字段验证之后、去重检查之前。

```python
# 跳过支付状态为「定金」的记录
payment = str(row.get('支付状态', '')).strip()
if payment == '定金':
    logger.info(f"跳过第{row_num}行(编号:{prescription_id})：支付状态为定金")
    continue
```

### 行为

- 跳过时只写入日志，不报错、不中断导入流程
- 其他记录正常处理（覆盖更新或新增）
- `prescription_id` 在检查前已提取，日志中可追溯
