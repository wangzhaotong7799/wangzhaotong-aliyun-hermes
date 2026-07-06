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

## Common query patterns

### Monthly report (by import time)

This is the user's standard monthly view — used by the `gaofang-monthly-report` cron job (每月1日08:00):

```
月份 | 上传患者人数 | 上传总料数 | 发放患者数 | 发放料数
```

See `gaofang-monthly-report` skill for the exact SQL template and cron configuration.

### Year-over-year comparison

When the user asks to compare two periods (e.g., 2025 H1 vs 2026 H1):

1. Query both periods using the SAME time dimension (either both by `date` or both by `created_at`)
2. For YoY comparison, use `date` (处方日期) as the dimension — both years have prescription dates, but `created_at` may not span both years
3. Present side-by-side: month | Year1患者 | Year1料数 | Year2患者 | Year2料数
4. Add totals row with cross-period patient dedup (NOT sum of monthly patients)

## Pitfalls

### Cross-month total dedup

**NEVER sum the monthly unique patient counts to get a half-year/year total.** The same patient may appear in multiple months. Always use a single query with the full date range:

```sql
-- ❌ Wrong: sum monthly counts
56 + 191 + 147 + 254 + 191 + 174 = 1013

-- ✅ Right: single dedup over the full range
COUNT(DISTINCT patient_name || '|' || age::text || '|' || COALESCE(patient_phone, ''))
FROM prescription_records
WHERE date >= '2025-01-01' AND date < '2025-07-01';
-- → 854
```

### Excel cross-reference for data verification

When the user sends an Excel file (e.g., `代煎处方 2026-06.xlsx`) to verify database numbers:

1. Extract the file with Python/openpyxl
2. Count total rows and sum `料数` (column index 9 in the export format)
3. Note: the user's "6月" Excel may contain prescriptions with dates in May (处方日期是5月但6月才导入)
4. Cross-reference: DB records where `created_at` is in the target month but `prescription_id` is NOT in the Excel → these are the extra records
5. Present the discrepancy clearly: "Excel有X条/Y料，DB多出N条/M料"
6. The `date` field (处方日期) may be in a different month than `created_at` — this is expected for batch imports

### Date field confusion

When the user asks for "上传" data:
- **上传时间 = `created_at`** (import/created timestamp) — this is the user's preferred time dimension for monthly stats
- **处方日期 = `date`** — when the prescription was written, NOT when it was imported
- An Excel file imported in June may contain prescriptions dated in May
- Always clarify which time dimension the user wants, or default to `created_at` for monthly reports

## Reference files

- `references/excel-cross-verify.md` — Step-by-step workflow for verifying database numbers against a user-provided import Excel file. Use when the user says "你的数据不对" and sends the original Excel.
