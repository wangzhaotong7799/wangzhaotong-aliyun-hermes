---
name: gaofang-database
description: Query the gaofang_v2 PostgreSQL database — monthly statistics, import analysis, status reports, patient dedup. Covers connection method, key tables, field semantics, and the user's preferred aggregation conventions.
version: 1.1.0
tags: [gaofang, database, postgresql, statistics]
related_skills: [gaofang-monthly-report]
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

## Import rules (import_template.py)

When Excel data is imported via `import_template.main()`:

| 规则 | 行为 |
|:----|:----|
| 重复处方编号 | **覆盖更新**（保留复诊/审计字段，其余全量覆盖） |
| 状态 | 强制设为 `'欠药'` |
| 是否传方 | 强制设为 `'已传方'` |
| 处方日期 | **强制设为导入当日** `date.today()`（忽略Excel中的处方日期） |
| 料数空 | 默认 `1` |
| 医助空 | 默认 `'-'` |
| 支付状态=定金 | **跳过该条**（2026-07-15新增规则，不报错、不中断） |

### Import result message

Result format after import (2026-07-15 update):
```
导入完成: 新增 2 条, 覆盖更新 10 条, 合计 18 料
```
The total 料数 is accumulated from `quantity` for both new AND updated records during processing. Skipped records (e.g., 定金) are NOT counted in the 合计.

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

**Historical data note:** 2025年及更早的处方全部是在2026年3月一次性批量导入的（`created_at`集中在2026-03-18至2026-03-31）。因此按`created_at`统计2025年数据会全部归到2026年3月，不反映各月真实新增。跨年对比时应统一使用 `date`（处方日期）口径。

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

## Backup & Restore（备份与恢复）

### 自动备份机制

| 任务 | 时间 | 脚本 | 输出 | 保留 |
|---|---|---|---|---|
| 数据库每日备份 | 每天 03:00（系统 crontab） | `/workspace/scripts/backup_gaofang_db.sh` | `/workspace/backups/db/gaofang_v2_YYYYMMDD.sql`（pg_dump 纯 SQL） | 15 天自动清理 |
| 手动按需备份 | 无 | `gaofang-v2/backup_db.py` | `gaofang-v2/backups/gaofang_v2_YYYYMMDD_HHMMSS.sql.gz`（gzip，支持恢复） | 手动清理 |
| Hermes 配置备份 | 每天 02:00 | `/root/.hermes/scripts/hermes-backup.sh` | `/root/hermes-backup/hermes-backup-*.tar.gz` | 14 天 |
| Hermes 配置→GitHub | 每天 23:00 | `~/.hermes/scripts/daily-backup.sh` | wangzhaotong-hermes 仓库 | 配置归档 7 天 |

### ⚠️ 备份失败排查（2026-08-07~12 连续 6 天静默失败案例）

**症状**：`/workspace/backups/db/` 缺当天文件；`backup.log` 尾部出现：
```
pg_dump: error: query failed: ERROR: permission denied for sequence xxx_id_seq
```
**根因**：用 postgres 超级用户新建表（如 RBAC 重构新增 groups / doctor_user_doctors）后，未给应用用户 `gaofang_app` 授权其序列 → pg_dump 报错中断，脚本删掉失败文件，**不告警、静默持续多天**。

**修复**：
```bash
su - postgres -c "psql -d gaofang_v2 -c \"GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO gaofang_app;\""
su - postgres -c "psql -d gaofang_v2 -c \"GRANT ALL ON ALL TABLES IN SCHEMA public TO gaofang_app;\""
```

**预防（已配置 2026-08-12，防复发）**：
```sql
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public GRANT ALL ON TABLES TO gaofang_app;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public GRANT ALL ON SEQUENCES TO gaofang_app;
```

**健康检查要点**：备份失败不告警 → 检查时**先看 backup.log 尾部**，不要只看目录里有没有文件；修复后手动跑 `bash /workspace/scripts/backup_gaofang_db.sh` 验证，并用 `grep -c "^COPY"` 确认关键表（prescription_records/users/groups/doctor_user_doctors）数据在内（pg_dump 默认 COPY 格式，`INSERT INTO` 计数为 0 是正常的）。

### crontab 残留清理

宝塔面板解绑后，系统 crontab 可能残留 `/www/server/cron/<hash>` 失效条目（目录已不存在）→ 每晚空跑。清理：先 `crontab -l > /root/crontab_backup_<date>.txt` 备份，再 `crontab -l | grep -v '<hash>' | crontab -`。面板解绑/迁移后应检查 crontab 残留。

详细备份/恢复操作见 `references/backup-and-restore.md`。

## Reference files

- `references/backup-and-restore.md` — 备份机制全貌、备份失败排查修复、pg_dump 恢复流程
- `references/excel-cross-verify.md` — Step-by-step workflow for verifying database numbers against a user-provided import Excel file. Use when the user says "你的数据不对" and sends the original Excel.
- `references/import-skip-rules.md` — Import rule change log: 支付状态=定金跳过规则（2026-07-15）
