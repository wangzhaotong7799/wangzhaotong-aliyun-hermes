---
name: gaofang-import-system
description: 膏方融合版V2 外部系统Excel导入 — import_template.py 的架构、列映射、默认值约定和排错指南
---

# Gaofang Excel Import System

## Overview

膏方融合版V2 (`gaofang-v2-fusion`) 从外部系统（广积德系统）导出的 `代煎导出` Excel 中批量导入处方数据。

入口：`POST /api/import` → `prescriptions.py::import_data()` → `import_template.py::main()`

核心模块：`/root/projects/drug-distribution-system/gaofang-v2/import_template.py`
导入 API 入口：`/root/projects/drug-distribution-system/gaofang-v2/api/v1/prescriptions.py`（第 538-574 行）
列表排序：`/root/projects/drug-distribution-system/gaofang-v2/api/v1/prescriptions.py`（第 164 行）
数据库模型：`/root/projects/drug-distribution-system/gaofang-v2/models/prescription.py`
服务进程：`gaofang-v2-fusion.service`（venv38 + gunicorn）

## Architecture

```
用户上传Excel → prescriptions.py import_data()
                    ↓
              保存到 uploads/ 目录
                    ↓
              设置 import_template.excel_file = 文件路径
                    ↓
              调用 import_template.main()
                    ↓
              解析Excel → 构建 record_data → 覆盖更新/新增 → 批量写入数据库
                    ↓
              返回 result_msg（含新增/覆盖/失败计数）
                    ↓
              prescriptions.py 返回 jsonify({"message": result_msg})
```

**关键流程修正**（2026-05-04）：`record_data` 必须在去重判断之前构建，否则会报 `referenced before assignment`。

## Column Mapping

Excel 来源：**广积德系统「代煎导出」格式**，非系统内置导入模板。

| Excel 列名 | 数据库字段 | 处理说明 |
|------------|-----------|---------|
| 处方日期 | date | 支持 "2026-04-27 09:01:02" 等含时间格式 |
| 处方编号 | prescription_id | 去重依据，唯一约束 |
| 患者姓名 | patient_name | 必填 |
| 患者性别 | gender | 必填 |
| 患者年龄 | age | 自动去除 "岁" 后缀 |
| 处方模板 | prescription_type | |
| 代煎料型 | decoction_material_type | |
| 代煎方型 | decoction_prescription_type | |
| 料数 | quantity | 整数转换 |
| 医生姓名 | doctor | 必填 |
| 医助 | assistant | 空时填 `-`（DB NOT NULL 约束） |
| 支付状态 | payment_status | |
| 收款状态 | collection_status | |
| 代煎克重 | decoction_weight | 字符串 |
| 饮片费用 | herbal_medicine_cost | 字符串 |
| 加工费用 | processing_cost | 字符串 |
| 患者手机号 | patient_phone | 可为空 |
| 快递地址 | express_address | |

**忽略的列**：门店、推荐人（无对应数据库字段）
**不读Excel的列**：代煎状态（见下文默认值）

## Fixed Defaults（不读Excel，统一硬编码）

| 字段 | 固定值 | 原因 |
|------|--------|------|
| status | `欠药` | 导入数据一律为待取状态，不读 Excel 的「代煎状态」列 |
| is_prescription_sent | `已传方` | 外系统导出数据皆为已传方 |

## 空值处理

| 字段 | Excel空值时 |
|------|------------|
| 医助(assistant) | 填 `-`（DB 列设为 NOT NULL，不能存 NULL） |
| 患者手机号(patient_phone) | 存 NULL（DB 列允许空） |
| 料数(quantity) | 默认 1 |
| 其他可选字段 | 存 NULL |

## 重复数据处理策略：覆盖更新 + 提示

**不是跳过重复**，而是覆盖更新。用户偏好为「覆盖+提示」：

1. **新建记录**：prescription_id 不存在时，创建新行
2. **覆盖更新**：prescription_id 已存在时：
   - **保留的字段**（不覆盖）：`id`, `created_at`, `updated_at`, `follow_up_status`, `follow_up_1_*`, `follow_up_2_*`, `follow_up_3_*`
   - **覆盖的字段**：除保留字段外的所有数据字段，包括日期、费用、医生、医助等
   - status 统一强制设为 `欠药`
3. **结果提示格式**：`"新增 X 条，覆盖更新 Y 条"`（由 import_template.main() 返回，prescriptions.py 直接作为 message 返回）

## Sort Order

**按 `id DESC` 排序**（用户要求，不要改为 `updated_at` 排序）。

代码位置：`prescriptions.py` 第 164 行
```python
query = query.order_by(PrescriptionRecord.id.desc())
```

> ⚠ **改排序风险**：曾改为 `updated_at.desc()` 但用户明确要求改回 `id.desc()`。不要再尝试改成其他排序方式。

### 排序失效的根因：ID 序列落后于已有数据

**现象**：新导入的数据排到了列表末尾，而非最前面。用户报告"刚导入的5条到了欠药数据的最后面"。

**根因**：V1→V2 迁移时，V1 数据保留了高 ID（如 5096~5197），但 PostgreSQL 自增序列（sequence）未更新到 `max(id)+1`，导致新记录只拿到低 ID（如 3497~3501）。按 `id DESC` 排序时，V1 旧数据（高 ID 但时间更早）反而排在最前。

**诊断方法**：
```sql
-- 检查序列是否落后
SELECT last_value, is_called FROM prescription_records_id_seq;
SELECT MIN(id) AS min_id, MAX(id) AS max_id, COUNT(*) FROM prescription_records;
-- 如果 max(id) > last_value，则序列落后
```

**修复方法**：重排 ID 使连续 + 重置序列（详见 `references/id-renumbering.md`）

## 日期解析能力

`_parse_date()` 支持以下格式：
- `"2026-04-27 09:01:02"`（含时间完整格式）
- `"2026-04-27"` / `"2026/04/27"` / `"2026.04.27"`
- `"2026年4月27日"`（中文格式）
- `20260427`（纯数字8位整型）
- Python `datetime` / `date` 对象（openpyxl 直接返回的）

## 结果消息传递机制

```
import_template.main() 返回 str
    正常情况：返回 result_msg（含计数）
    有失败行：raise ValueError(result_msg) → 被 prescriptions.py 的 except 捕获 → 返回 400
```

prescriptions.py 第 569 行：
```python
result_msg = import_template.main()
return jsonify({"message": result_msg})
```

不直接返回 `"数据导入成功"`，而是返回 import_template 生成的详细报告。

## Known Pitfalls

### 1. `assistant` 列 NOT NULL 约束
DB 定义为 `nullable=False`，空值**必须**填占位符（当前用 `-`）。如果从 REQUIRED_FIELDS 中移除，必须在 DEFAULT_VALUES 中设置默认值。

### 2. `record_data` 必须在去重判断之前构建
**错误写法**：先判断 `prescription_id in existing_ids`，再构建 `record_data` → 报 `local variable 'record_data' referenced before assignment`
**正确顺序**：验证必填 → 构建 `record_data`（含字段映射、固定值、天数计算）→ 判断存在性 → 覆盖/新增

### 3. 外部导出格式变更
列名绑定了广积德系统「代煎导出」格式。如果来源系统变更，需更新 COLUMN_MAP。

### 4. 大批量导入性能
首次查询已有 prescription_id 是 SELECT ALL，大量数据时可能较慢。

### 5. `Transaction was rolled back`
某行失败后 session 损坏，后续行报 `This Session's transaction has been rolled back due to a previous exception during flush`。
**解决**：失败时调用 `session.rollback()` 重置状态，或让外层 except 统一处理。

### 6. 推送仓库时 gaofang-v2/ 嵌套 .git
`gaofang-v2/` 内部可能残留 `.git` 目录（初始化或 clone 时遗留），会导致父仓库将其识别为 **gitlink（子模块）** 而非普通目录。
**表现**：`git add gaofang-v2/` 只显示一行 `Am gaofang-v2`，`git ls-files --stage` 显示 `160000` 模式。
**解决**：
```bash
git rm --cached -rf gaofang-v2/
rm -rf gaofang-v2/.git
git add gaofang-v2/
```

## Troubleshooting

### 400 BAD REQUEST / 导入失败
- 检查 Excel 列名是否匹配「代煎导出」格式（不是系统内置导入模板）
- 检查必填字段是否非空（处方编号、患者姓名、患者性别、患者年龄、医生姓名）
- prescription_id 已存在会覆盖，但字段映射错误仍会报错

### NOT NULL 约束违反
- 通常是 `assistant` 字段为空 → DEFAULT_VALUES 已设 `-`
- 检查新增 NOT NULL 列是否已处理

### Python 模块找不到
- `import import_template` 是懒加载（函数体内 import），模块必须位于 `gaofang-v2/` 目录下
- 放置位置与 `app.py`、`config.py`、`database.py` 同级

### 导入后数据显示位置异常（新数据排到最后）
- 按 `id DESC` 排序，新记录（id 最大）应排最前
- 如果新数据排到了最后，说明 **自增序列落后**（`max(id) > last_value`）
- 解决方式：执行 ID 重排流程（详见 `references/id-renumbering.md`）
- 覆盖更新的记录 id 不变，位置不动
