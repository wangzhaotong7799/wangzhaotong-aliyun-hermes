# Gaofang V2 — Sequence & ID Gap Real-World Diagnosis

**Date**: 2026-05-05  
**Source session**: V2 system sort order investigation  
**Tech stack**: Flask 2.0.3 + SQLAlchemy 1.4.46 + PostgreSQL 14 + Python 3.8

---

## Problem Statement

User imported 5 new records into the V2 system. Expected them at the **top** of the list (newest first). They appeared at the **bottom**, after older V1 migrated data.

## Diagnosis

### 1. Check sort logic

**Backend** (`api/v1/prescriptions.py`, line 164):
```python
query = query.order_by(PrescriptionRecord.id.desc())
```

Sort order is correct — `id DESC` should put newest (highest id) first.

**Mobile frontend** (`static/mobile/js/page-pickup.js`): No client-side re-sorting — relies on backend order.

### 2. Query API directly

```bash
curl -s 'http://localhost:8080/api/prescriptions?status=欠药&page=1&per_page=60'
```

Result: 53 records, sorted by id DESC, IDs 5197 → 3490.

### 3. Query database directly

```sql
SELECT MIN(id), MAX(id) FROM prescription_records WHERE status = '欠药';
-- MIN: 3490, MAX: 5197

SELECT last_value FROM prescription_records_id_seq;
-- 3501

-- Latest by created_at
SELECT id, prescription_id, patient_name, created_at
FROM prescription_records ORDER BY created_at DESC LIMIT 5;
-- id=3501, 3500, 3499, 3498, 3497 → created 2026-05-05 00:49:44 (today's import!)

-- Highest IDs
SELECT id, prescription_id, patient_name, created_at
FROM prescription_records ORDER BY id DESC LIMIT 5;
-- id=5197, 5196, 5195, 5194, 5193 → created 2026-04-30 (V1 migration data!)
```

### 4. Root Cause

V1 data was migrated into PostgreSQL with **original IDs preserved** (5190-5197 range). But the PostgreSQL auto-increment **sequence was not updated** — it stayed at 3501. New records get IDs 3497-3501, which are **lower** than V1 data (5197).

When sorted by `id DESC`: V1 (April) on top, new (May) on bottom. **Backwards.**

## Gap Analysis

```sql
SELECT 
  MIN(id), MAX(id), COUNT(*),
  (MAX(id)-MIN(id)+1) AS id_range,
  (MAX(id)-MIN(id)+1)-COUNT(*) AS gaps
FROM prescription_records;
-- Result: MIN=1, MAX=5197, COUNT=3505, gaps=1692

-- Detailed gaps:
WITH numbered AS (
  SELECT id, LAG(id) OVER (ORDER BY id) AS prev_id
  FROM prescription_records
)
SELECT (prev_id+1) AS gap_start, (id-1) AS gap_end, (id-prev_id-1) AS gap_size
FROM numbered WHERE id - prev_id > 1
ORDER BY gap_start;
```

Key gaps:
- **3281→3483**: 203 holes — sequence drop during migration
- **3502→4970**: 1469 holes — sequence stayed at 3501 while V1 data used 5096-5197

## Solution Proposed (not yet executed)

1. Delete 5 new records (IDs 3497-3501)
2. Renumber all records: `UPDATE ... SET id = ROW_NUMBER() OVER (ORDER BY id)`
3. Reset sequence to `MAX(id) + 1`

This makes IDs consecutive (1-3500), so new records will always get higher IDs and sort correctly by `id DESC`.

## FK Check (confirmed safe)

```sql
SELECT table_name, column_name FROM information_schema.table_constraints tc
JOIN information_schema.key_column_usage kcu ON tc.constraint_name = kcu.constraint_name
JOIN information_schema.constraint_column_usage ccu ON ccu.constraint_name = tc.constraint_name
WHERE tc.constraint_type = 'FOREIGN KEY'
  AND ccu.table_name = 'prescription_records' AND ccu.column_name = 'id';
-- Returns: 0 rows → no FK references to id
```

`status_change_logs` references `prescription_id` (the business key / 代煎号), not the DB `id`.
