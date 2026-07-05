---
name: gaofang-database
description: Query the gaofang_v2 PostgreSQL database — monthly statistics, import analysis, status reports, patient dedup. Covers connection method, key tables, field semantics, and the user's preferred aggregation conventions.
version: 1.0.0
---

# Gaofang Database (gaofang_v2 PostgreSQL)

When the user asks for data from the膏方管理系统 V2.

## Connection

```bash
su - postgres -c "psql -d gaofang_v2 -c 'YOUR QUERY HERE'"
```

The database owner/role is `gaofang_app`. The above command runs as the `postgres` system user which has superuser access.

## Key Table: `prescription_records`

### Field semantics (critical — get these right)

| Column | Meaning | Notes |
|--------|---------|-------|
| `date` | **处方日期** (prescription date) | When the prescription was written, NOT when it was imported |
| `created_at` | **导入时间** (import/created timestamp) | When the record was added to the system. **User wants monthly stats by this field** |
| `quantity` | **料数** (number of 膏方 units) | Default 1 on import. This IS the 料数 field |
| `decoction_weight` | 代煎克重 (weight in grams) | Separate from quantity |
| `patient_name` | 患者姓名 | |
| `age` | 患者年龄 | Integer |
| `patient_phone` | 患者手机号 | Can be NULL/empty (电话允许空) |
| `status` | 状态 | One of: 已取, 已邮寄, 未取, 欠药, 已退药 |
| `is_prescription_sent` | 是否传方 | Default: '已传方' |
| `doctor` | 医生姓名 | |
| `assistant` | 医助 | Default: '-' when empty |
| `prescription_id` | 处方编号 | Unique |

### Status semantics

- **已取** + **已邮寄** = **发放** (dispensed/given to patient)
- **未取** + **欠药** = 未发放 (pending)
- **已退药** = returned/cancelled

### Patient dedup logic (user's rule)

> 按姓名+年龄+电话号去重，三个都一样视为一个患者。

```sql
COUNT(DISTINCT patient_name || '|' || age::text || '|' || COALESCE(patient_phone, ''))
```

Treat NULL phone as `''` for grouping purposes.

## Standard monthly statistics query

The user's preferred output format is a table with exactly 5 columns:
**月份 | 上传患者人数 | 上传总料数 | 发放患者数 | 发放料数**

Key rules:
1. **Group by `created_at` (导入时间), NOT `date` (处方日期)** — this is the user's explicit preference
2. **患者人数 = dedup by (name, age, phone)** — not raw record count
3. **发放 = status IN ('已取', '已邮寄')**

Template query:

```sql
WITH upload AS (
  SELECT 
    to_char(created_at::date, 'YYYY-MM') AS 月份,
    COUNT(DISTINCT patient_name || '|' || age::text || '|' || COALESCE(patient_phone, '')) AS 上传患者人数,
    SUM(quantity) AS 上传总料数
  FROM prescription_records
  WHERE created_at >= '<START>' AND created_at < '<END>'
  GROUP BY 月份
),
dispense AS (
  SELECT 
    to_char(created_at::date, 'YYYY-MM') AS 月份,
    COUNT(DISTINCT patient_name || '|' || age::text || '|' || COALESCE(patient_phone, '')) AS 发放患者数,
    SUM(quantity) AS 发放料数
  FROM prescription_records
  WHERE created_at >= '<START>' AND created_at < '<END>'
    AND status IN ('已取', '已邮寄')
  GROUP BY 月份
)
SELECT 
  u.月份,
  u.上传患者人数,
  u.上传总料数,
  COALESCE(d.发放患者数, 0) AS 发放患者数,
  COALESCE(d.发放料数, 0) AS 发放料数
FROM upload u
LEFT JOIN dispense d ON u.月份 = d.月份
ORDER BY u.月份;
```

## Import defaults (from import_template.py)

When Excel data is imported, empty/missing fields get these defaults:
- 料数 (quantity) → 1
- 医助 (assistant) → '-'
- 是否传方 (is_prescription_sent) → '已传方'

## Data presentation rules

- Deliver ONLY the requested columns — no extra commentary, no interpretations, no "趋势分析" unless asked
- If the user says "只要 月份 | A | B | C | D", output exactly those columns
- For data discrepancies, state the facts concisely and ask the user what they expect — don't argue
