# Gaofang Import System — Architecture and Column Mapping Reference

> **Absorbed from `gaofang-import-system`** (2026-05-22 consolidated into `flask-postgresql-system-upgrade`)
>
> This file preserves the generalizable patterns from the gaofang-v2 import system. Project-specific file paths and business logic have been generalized.

## Architecture

```
User uploads Excel → API handler (prescriptions.py)
                    ↓
               Save to uploads/ directory
                    ↓
               Call import_template.main()
                    ↓
               Parse Excel → Map columns → Build records → Batch DB upsert
                    ↓
               Return result (counts: new/updated/failed)
```

**Key flow fix**: `record_data` must be built BEFORE dedup check to avoid `referenced before assignment`.

## Column Name Mapping Pattern

For flexible imports where source systems use different column naming conventions:

### Define mapping dictionary

```python
COLUMN_MAPPING = {
    # Standard template fields
    '日期': 'date',
    '编号': 'prescription_id',
    '姓名': 'patient_name',
    '性别': 'gender',
    
    # Custom user fields (alternative naming)
    '门店日期': 'date',
    '处方编号': 'prescription_id',
    '患者性别': 'gender',
    '患者年龄': 'age',
}
```

### Accept multiple acceptable headers for required fields

```python
required_fields = {
    'date': ['日期', '门店日期', '处方日期'],
    'prescription_id': ['编号', '处方编号', '代煎号'],
    'patient_name': ['姓名', '患者姓名'],
}

missing = []
for field, possible_headers in required_fields.items():
    found = any(ph in clean_headers for ph in possible_headers)
    if not found:
        missing.append(f"{'、'.join(possible_headers)}")
```

### Parse rows using mapped columns

```python
column_mapping = map_column_names(raw_headers)
row_data = {}
for col_idx, system_field in column_mapping.items():
    value = ws.cell(row=row_num, column=col_idx).value
    if value is not None:
        row_data[system_field] = value
```

## Duplicate Handling Strategy

For systems where the same record can be re-imported with updates:

1. **New record**: ID doesn't exist → INSERT
2. **Overwrite**: ID exists → UPDATE selected fields only
   - **Keep**: `id`, `created_at`, `updated_at`, status tracking fields
   - **Overwrite**: all data fields (dates, costs, doctor, assistant)
3. **Result format**: `"新增 X 条，覆盖更新 Y 条"`

## Date Parsing (multi-format)

```python
def _parse_date(value):
    """Support multiple date formats"""
    if isinstance(value, (datetime, date)):
        return value.date() if isinstance(value, datetime) else value
    if isinstance(value, (int, float)):
        value = str(int(value))
    # Strip time portion: "2026-04-27 09:01:02" → date
    value = str(value).strip()
    # Try common formats...
```

## NOT NULL Constraint Handling

When a column is `nullable=False` in the database but the source Excel may have empty cells:
- Set a DEFAULT_VALUE for empty cases
- Example: `assistant` → fill with `'-'` placeholder
- Don't remove the field from REQUIRED_FIELDS without also setting a default

## Database Sequence Sync (PostgreSQL)

When ID sequence lags behind existing data (new records get lower IDs than old ones):

### Diagnosis

```sql
SELECT last_value, is_called FROM your_table_id_seq;
SELECT MIN(id) AS min_id, MAX(id) AS max_id, COUNT(*) FROM your_table;
```

If `max(id) > last_value`, the sequence is outdated — new records will get IDs smaller than old ones.

### Fix (no foreign key dependencies)

```sql
BEGIN;
-- Drop PK constraint
ALTER TABLE your_table DROP CONSTRAINT your_table_pkey;

-- Renumber sequentially
WITH renumbered AS (
  SELECT id AS old_id, ROW_NUMBER() OVER (ORDER BY id) AS new_id
  FROM your_table
)
UPDATE your_table t SET id = r.new_id FROM renumbered r WHERE t.id = r.old_id;

-- Rebuild PK and reset sequence
ALTER TABLE your_table ADD PRIMARY KEY (id);
SELECT setval('your_table_id_seq', COALESCE((SELECT MAX(id) FROM your_table), 1));
COMMIT;
```

## Batch Import Transaction Handling

**Problem**: One row failure → session corrupted → subsequent rows get `"This Session's transaction has been rolled back due to a previous exception during flush"`

**Fix**: On failure, call `session.rollback()` to reset state, or let outer `except` handle it uniformly. Wrap each batch in a try/except with rollback.

## Git Submodule Trap

**Problem**: Copying a project into a monorepo causes nested `.git` directory, which git interprets as a gitlink (submodule) rather than a regular directory.

**Symptoms**: `git add project/` shows one line `Am project`, `git ls-files --stage` shows `160000` mode.

**Fix**:
```bash
git rm --cached -rf project/
rm -rf project/.git
git add project/
```
