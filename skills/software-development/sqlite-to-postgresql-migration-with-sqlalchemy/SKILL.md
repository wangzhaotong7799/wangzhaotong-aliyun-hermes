---
name: sqlite-to-postgresql-migration-with-sqlalchemy
description: Complete workflow for migrating data from SQLite to PostgreSQL using SQLAlchemy, handling auto-increment ID conflicts and foreign key relationships.
version: 1.0.0
author: Hermes Agent (based on gaofang-v2 upgrade experience)
license: MIT
metadata:
  hermes:
    tags: [migration, database, sqlalchemy, sqlite, postgresql, legacy-system]
    related_skills: [flask-postgresql-system-upgrade, legacy-system-safe-refactoring]
---

# SQLite to PostgreSQL Data Migration with SQLAlchemy

**Purpose**: Complete workflow for migrating data from SQLite to PostgreSQL using SQLAlchemy, preserving relationships while handling auto-increment ID conflicts.

**When to Use**: 
- Upgrading legacy applications from SQLite to PostgreSQL
- Database migration requiring foreign key preservation
- Python 3.6+ environments with SQLAlchemy 1.4
- Production systems where data integrity is critical

---

## Key Challenge: Auto-Increment ID Mismatch

SQLite's `AUTOINCREMENT` and PostgreSQL's `SERIAL` generate different IDs even with identical inserts. Simply preserving old IDs causes **foreign key constraint violations**.

### Example of the Problem

```sql
-- SQLite source table
INSERT INTO users VALUES (1, 'admin', ...);
INSERT INTO roles VALUES (1, 'admin', ...);  
INSERT INTO user_roles VALUES (1, 1);  -- FK: user_id=1, role_id=1

-- When migrated to PostgreSQL:
INSERT INTO users VALUES (1, 'admin', ...);  -- Gets ID=1 ✅
INSERT INTO roles VALUES (1, 'admin', ...);  -- Gets ID=1 ✅
INSERT INTO user_roles VALUES (1, 1);  -- FAILS if IDs shifted during insert!
```

If the order of operations differs or sequences behave differently, you get errors like:

```
psycopg2.errors.ForeignKeyViolation: 
insert or update on table "role_permissions" violates foreign key constraint
DETAIL: Key (permission_id)=(1) is not present in table "permissions".
```

### Solution Strategy: Don't Preserve Old IDs

```python
# ✅ CORRECT APPROACH: Build ID mapping during migration
old_id_to_new_id = {}

for row in sqlite_cur.fetchall():
    result = conn.execute(Model.__table__.insert().values(**data))
    # SQLAlchemy 1.4 returns column names as keys
    new_id = list(result.inserted_primary_key)[0]
    if new_id is None:  # Fallback for certain configurations
        new_id_result = conn.execute(text("SELECT currval('tablename_id_seq')")).fetchone()
        new_id = new_id_result[0]
    old_id_to_new_id[row['id']] = new_id

# Later, use mapped IDs for relationship tables
conn.execute(relationship_table.insert().values(
    parent_id=old_id_to_new_id[old_parent_id],
    child_id=old_id_to_new_id[old_child_id]
))
```

---

## Common Pitfalls & Solutions

### Problem 1: SQLAlchemy 1.4 vs 2.0 API Differences

**Symptom**: `KeyError: 0` when accessing inserted IDs

```python
# ❌ WRONG (SQLAlchemy 2.0+)
new_id = dict(result.inserted_primary_key)[0]

# ✅ CORRECT (SQLAlchemy 1.4)
new_id = list(result.inserted_primary_key)[0]

# Alternative fallback if still None
if new_id is None:
    new_id_result = conn.execute(text("SELECT currval('tablename_id_seq')")).fetchone()
    new_id = new_id_result[0]
```

**Why**: In SQLAlchemy 1.4, `inserted_primary_key` is a `KeyedTuple`, not a dict. Using it directly gives the first value, but `dict()` conversion expects numeric keys which don't exist.

### Problem 2: Foreign Key Constraint Errors During Migration

**Symptom**: `Foreign Key Violation` despite correct mapping

```python
# ❌ DON'T: Try to disable FK with session_replication_role
with pg_engine.begin() as conn:
    conn.execute(text("SET session_replication_role = 'replica';"))  # Permission denied!
```

**Root Cause**: Regular users can't set `session_replication_role`. Need superuser privileges.

```python
# ✅ DO THIS: Drop all, recreate clean, then migrate in order
Base.metadata.drop_all(engine)  # Nukes existing tables + constraints
Base.metadata.create_all(engine)  # Creates fresh schema

# Then migrate in strict dependency order:
# 1. Tables without FKs first (permissions, roles, users)
# 2. Tables with FKs second (using ID mappings)  
# 3. Many-to-many relationship tables last (user_roles, role_permissions)
```

### Problem 3: Model Schema Drift

**Symptom**: Column doesn't exist / Unconsumed column names

```python
# V1 SQLite schema
CREATE TABLE prescription_records (
    id INTEGER PRIMARY KEY,
    decoction_material_type VARCHAR(50),  -- Added later
    ...
);

# V2 SQLAlchemy model (created before checking actual V1 schema)
class PrescriptionRecord(Base):
    __tablename__ = 'prescription_records'
    # Missing decoction_material_type field!
```

**Solution**: Always verify actual source schema first:

```bash
sqlite3 source.db ".schema tablename"
# Compare output with SQLAlchemy model columns programmatically
```

Or force recreate after model updates:

```python
# Force pick up new columns
Base.metadata.drop_all(engine)
Base.metadata.create_all(engine)
```

### Problem 4: Connection Context Management

**Symptom**: `'Connection' object has no attribute 'commit'`

```python
# ❌ WRONG: Manual transaction management with wrong connection type
with pg_engine.connect() as conn:
    # ...
    conn.commit()  # AttributeError!

# ✅ CORRECT: Use begin() context manager
with pg_engine.begin() as conn:
    # ...
    # Auto-commits or rollbacks automatically
```

---

## Complete Migration Script Template

```python
#!/usr/bin/env python3
"""
Data Migration: SQLite → PostgreSQL
Author: Implementation Engineer
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

import sqlite3
from datetime import datetime
from sqlalchemy import create_engine, text
from models import User, Role, Permission, user_roles, role_permissions, Base

def migrate_data():
    print("\n🔄 Starting Data Migration...")
    
    # Connect to both databases
    print("Connecting to SQLite...")
    sqlite_conn = sqlite3.connect('/path/to/source.db')
    sqlite_conn.row_factory = sqlite3.Row
    
    print("Connecting to PostgreSQL...")
    pg_engine = create_engine('postgresql://user:pass@localhost/dbname', 
                              pool_pre_ping=True)
    
    # Clean slate - ensures schema matches current models
    print("Recreating PostgreSQL schema...")
    Base.metadata.drop_all(pg_engine)
    Base.metadata.create_all(pg_engine)
    
    start_time = datetime.now()
    
    try:
        with pg_engine.begin() as conn:
            sqlite_cur = sqlite_conn.cursor()
            
            # ========== STEP 1: MIGRATE PARENT TABLES (build ID mappings) ==========
            
            # Permissions (no dependencies)
            print("[1/5] Migrating permissions...")
            sqlite_cur.execute("SELECT name, description FROM permissions")
            for row in sqlite_cur.fetchall():
                conn.execute(Permission.__table__.insert().values(
                    name=row[0], description=row[1]))
            print(f"  ✓ {len(list(sqlite_cur.execute('SELECT * FROM permissions').fetchall()))} permissions")
            
            # Roles (depends on nothing)
            print("[2/5] Migrating roles...")
            sqlite_cur.execute("SELECT id, name, description FROM roles")
            role_map = {}
            for row in sqlite_cur.fetchall():
                result = conn.execute(Role.__table__.insert().values(
                    name=row[1], description=row[2]))
                new_id = list(result.inserted_primary_key)[0]
                role_map[row[0]] = new_id
            print(f"  ✓ {len(role_map)} roles (ID map created)")
            
            # Users (depends on nothing)
            print("[3/5] Migrating users...")
            sqlite_cur.execute("SELECT id, username, email, password_hash FROM users")
            user_map = {}
            for row in sqlite_cur.fetchall():
                result = conn.execute(User.__table__.insert().values(
                    username=row[1], email=row[2], password_hash=row[3]))
                new_id = list(result.inserted_primary_key)[0]
                user_map[row[0]] = new_id
            print(f"  ✓ {len(user_map)} users (ID map created)")
            
            # ========== STEP 2: MIGRATE RELATIONSHIPS (use ID mappings) ==========
            
            print("[4/5] Migrating relationships...")
            
            # user_roles
            sqlite_cur.execute("SELECT user_id, role_id FROM user_roles")
            for row in sqlite_cur.fetchall():
                conn.execute(user_roles.insert().values(
                    user_id=user_map[row['user_id']],
                    role_id=role_map[row['role_id']]))
            
            # role_permissions
            sqlite_cur.execute("SELECT role_id, permission_id FROM role_permissions")
            perm_map = {}
            sqlite_cur.execute("SELECT id, name FROM permissions")
            for row in sqlite_cur.fetchall():
                perm_map[row[0]] = row[1]  # We'll need to lookup by name
            
            # Re-query permissions from PG to get NEW IDs
            pg_perms = conn.execute(text("SELECT id, name FROM permissions")).fetchall()
            perm_name_to_new_id = {row.name: row.id for row in pg_perms}
            
            sqlite_cur.execute("SELECT role_id, permission_id FROM role_permissions")
            for row in sqlite_cur.fetchall():
                perm_name = sqlite_cur.execute(
                    "SELECT name FROM permissions WHERE id=?", 
                    (row['permission_id'],)
                ).fetchone()[0]
                new_perm_id = perm_name_to_new_id[perm_name]
                
                conn.execute(role_permissions.insert().values(
                    role_id=role_map[row['role_id']],
                    permission_id=new_perm_id))
            
            print(f"  ✓ Relationships migrated successfully")
            
            # ========== STEP 3: MIGRATE CHILD TABLES (complex business data) ==========
            
            print("[5/5] Migrating prescription records...")
            sqlite_cur.execute("""
                SELECT date, prescription_id, patient_name, ... all fields ...
                FROM prescription_records
            """)
            rx_count = 0
            for row in sqlite_cur.fetchall():
                conn.execute(PrescriptionRecord.__table__.insert().values(
                    date=row[0], prescription_id=row[1], ...))
                rx_count += 1
            print(f"  ✓ {rx_count} prescription records")
        
        duration = (datetime.now() - start_time).total_seconds()
        print(f"\n✅ Migration completed in {duration:.1f} seconds!")
        return True
        
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = migrate_data()
    exit(0 if success else 1)
```

---

## Python 3.6 Compatibility Notes

Since many legacy systems run on older Python versions, lock compatible package versions:

| Library | Compatible Version | Note |
|---------|-------------------|------|
| Flask | 2.0.3 | Last version supporting Py3.6 |
| SQLAlchemy | 1.4.46 | Full compatibility, use `list()` for primary keys |
| Flask-SQLAlchemy | 2.5.1 | Works with SA 1.4 |
| psycopg2-binary | 2.9.3 | PostgreSQL adapter |
| PyJWT | 2.4.0 | Token authentication |
| openpyxl | 3.0.10+ | Excel support (if needed) |

**requirements.txt example**:
```
Flask==2.0.3
Werkzeug==2.0.3
SQLAlchemy==1.4.46
Flask-SQLAlchemy==2.5.1
psycopg2-binary==2.9.3
PyJWT==2.4.0
python-dotenv==0.19.2
```

---

## Post-Migration: Fix PostgreSQL Auto-Increment Sequence

⚠️ **CRITICAL** — After migrating data with explicit IDs, PostgreSQL's sequence is NOT automatically updated.

### The Problem

When you migrate data preserving old IDs (e.g., V1→V2 migration with IDs like 5197), PostgreSQL's `SERIAL`/`IDENTITY` sequence still starts from wherever it was initialized (often 1 or a low number). New records get **lower IDs than old migrated data**, causing:

- `ORDER BY id DESC` shows **older data first** (migrated high IDs on top)
- Users see newly imported records at the **bottom of the list**
- Any logic relying on ID monotonicity breaks

### Detection

```sql
-- Compare sequence value vs actual max ID
SELECT last_value FROM tablename_id_seq;
SELECT MAX(id) FROM tablename;

-- If last_value << MAX(id) → sequence is behind!
```

In the gaofang-v2 case:
| Metric | Value | Issue |
|--------|-------|-------|
| `MAX(id)` | 5197 | V1 migrated data stays at high IDs |
| Sequence `last_value` | 3501 | Far behind max — new records get low IDs |
| Sort order | `id DESC` | Puts April data (ID 5197) before May data (ID 3501) 🚫 |

### Fix: Synchronize the Sequence

```sql
-- Set sequence to continue from max existing ID
SELECT setval('tablename_id_seq', (SELECT MAX(id) FROM tablename));
```

In a migration script using SQLAlchemy:

```python
from sqlalchemy import text

with engine.begin() as conn:
    result = conn.execute(text("SELECT MAX(id) FROM prescription_records")).fetchone()
    max_id = result[0]
    conn.execute(text(f"SELECT setval('prescription_records_id_seq', {max_id})"))
    print(f"✅ Sequence set to {max_id}")
```

### Alternative: Sort by created_at Instead

If you can't fix the sequence (shared DB, multiple apps), change the sort:

```python
# ❌ Broken: puts migrated data (high IDs) first
query = query.order_by(PrescriptionRecord.id.desc())

# ✅ Correct: always newest first regardless of ID discontinuity
query = query.order_by(PrescriptionRecord.created_at.desc(), PrescriptionRecord.id.desc())
```

This is the **safer semantic fix** — it doesn't depend on ID monotonicity.

### When This Happens

- After any data migration that preserves original IDs
- After bulk inserts with explicit `id` values
- After `SET IDENTITY_INSERT` / direct ID assignment
- Anytime you see "new records go to the bottom" in an `id DESC` sorted list

---

## Post-Migration Deep Dive: ID Gap Analysis & Renumbering

When the gap between `last_value` and `MAX(id)` is large enough to cause real business confusion (e.g., April data at ID 5197 shows before May data at ID 3501), **fixing the sequence isn't enough** — you need to decide between two strategies.

### Strategy Comparison

| Strategy | What It Does | When To Use | Data Impact |
|----------|------------|-------------|-------------|
| **Fix Sequence Only** | `SELECT setval('seq', MAX(id))` | Gaps are small, no sorting confusion | ✅ Zero — original IDs preserved |
| **Renumber All IDs** | Reassign IDs consecutively | Gaps are large, sorting by id is busted | ⚠️ ID column rewritten — requires no FK references to `id` |

### When Renumbering Makes Sense

The **key diagnostic** that tells you renumbering is worth it:

```sql
-- Run this diagnostic
SELECT 
  MIN(id) AS min_id,
  MAX(id) AS max_id,
  COUNT(*) AS total_records,
  (MAX(id) - MIN(id) + 1) AS id_range,
  (MAX(id) - MIN(id) + 1) - COUNT(*) AS total_gaps,
  ROUND(100.0 * (MAX(id) - MIN(id) + 1 - COUNT(*)) / (MAX(id) - MIN(id) + 1), 1) AS gap_pct
FROM prescription_records;
```

**Real example** (from gaofang-v2 migration):
| Metric | Value |
|--------|-------|
| MIN(id) | 1 |
| MAX(id) | 5197 |
| Total records | 3505 |
| ID range | 5197 |
| Total gaps | **1692** |
| Gap % | **32.5%** |

With 32% of IDs wasted, sorted by `id DESC`:
- **V1 migrated data** (April, IDs 5190-5197) appears **first** ← looks "newest"
- **V2 freshly imported data** (May, IDs 3490-3501) appears **last** ← looks "oldest"

This is exactly backwards from what users expect. Renumbering is the right fix here.

### Gap Analysis Tool

Find every hole in the ID sequence:

```sql
WITH numbered AS (
  SELECT id, LAG(id) OVER (ORDER BY id) AS prev_id
  FROM prescription_records
  WHERE id <= (SELECT MAX(id) FROM prescription_records)
)
SELECT (prev_id + 1) AS gap_start, (id - 1) AS gap_end, 
       (id - prev_id - 1) AS gap_size
FROM numbered
WHERE id - prev_id > 1
ORDER BY gap_start;
```

### Renumbering IDs — The Complete Recipe

**Prerequisites:**
- ✅ No FK constraints reference `prescription_records.id` (check with query below)
- ✅ Other tables reference records via business key (e.g., `prescription_id` / 代煎号), not DB `id`
- ✅ Application code doesn't hardcode ID values

**Step 1: Verify no FK references to `id`**

```sql
SELECT tc.table_name, kcu.column_name
FROM information_schema.table_constraints AS tc
JOIN information_schema.key_column_usage AS kcu
  ON tc.constraint_name = kcu.constraint_name
JOIN information_schema.constraint_column_usage AS ccu
  ON ccu.constraint_name = tc.constraint_name
WHERE tc.constraint_type = 'FOREIGN KEY'
  AND ccu.table_name = 'prescription_records'
  AND ccu.column_name = 'id';
```

If this returns zero rows → **safe to renumber**.

**Step 2: Delete records that would be reimported (optional)**

If the user plans to reimport certain records after renumbering, delete them first:

```sql
DELETE FROM prescription_records WHERE id IN (3497, 3498, 3499, 3500, 3501);
```

**Step 3: Renumber with ROW_NUMBER()**

```sql
UPDATE prescription_records t
SET id = t2.new_id
FROM (
  SELECT id, ROW_NUMBER() OVER (ORDER BY id) AS new_id
  FROM prescription_records
) t2
WHERE t.id = t2.id;
```

This reassigns IDs 1-N based on the current sort order (preserving relative ordering).

**Step 4: Reset the sequence**

```sql
ALTER SEQUENCE prescription_records_id_seq RESTART WITH N;
-- N = (SELECT MAX(id) FROM prescription_records) + 1
```

**Step 5: Verify**

```sql
SELECT MIN(id), MAX(id), COUNT(*),
       (MAX(id) - MIN(id) + 1) - COUNT(*) AS remaining_gaps
FROM prescription_records;
-- Expected: remaining_gaps = 0
```

### Caution: When NOT to Renumber

| Condition | Concern | Alternative |
|-----------|---------|------------|
| FK constraints reference `id` | Would break referential integrity | Fix the sequence only, or update FK targets |
| Other apps/tools hardcode ID references | Would break external integrations | Leave IDs as-is, change sort to `created_at DESC` |
| API consumers cache `id` values | Would cause stale cache lookups | Plan renumbering during maintenance window |
| You just need the *current* sort fixed | Symptom is mild | Change sort order instead: `ORDER BY created_at DESC, id DESC` |

### The Simplest Fix When Renumbering Is Too Heavy

```python
# In the query layer — no data changes needed
query = query.order_by(
    PrescriptionRecord.created_at.desc(),
    PrescriptionRecord.id.desc()  # tiebreaker
)
```

This is the **safest, zero-risk fix** — it always shows newest data first, regardless of ID discontinuities. Use this when:
- You can't do maintenance downtime
- The gaps don't bother you functionally
- You want to avoid touching the `id` column

---

## Verification Steps

After migration completes, verify data integrity:

```sql
-- 1. Check record counts match
SELECT COUNT(*) FROM users;           -- Should equal SQLite count
SELECT COUNT(*) FROM prescriptions;   -- Should equal SQLite count

-- 2. Verify foreign key integrity (should return 0 rows each)
SELECT ur.user_id 
FROM user_roles ur 
LEFT JOIN users u ON ur.user_id = u.id 
WHERE u.id IS NULL;

SELECT rp.permission_id
FROM role_permissions rp
LEFT JOIN permissions p ON rp.permission_id = p.id
WHERE p.id IS NULL;

-- 3. Test relationships work correctly
SELECT p.patient_name, c.old_status, c.new_status 
FROM prescription_records p
JOIN status_change_logs c ON p.prescription_id = c.prescription_id
LIMIT 5;

-- 4. Spot-check specific records
SELECT * FROM users WHERE username = 'admin';
SELECT * FROM prescription_records WHERE prescription_id = 'SPECIFIC-ID';
```

**Programmatic verification**:
```python
# Compare counts
sqlite_counts = {
    'users': sqlite_cur.execute('SELECT COUNT(*) FROM users').fetchone()[0],
    'prescriptions': sqlite_cur.execute('SELECT COUNT(*) FROM prescription_records').fetchone()[0],
}

pg_counts = {
    'users': conn.execute(text('SELECT COUNT(*) FROM users')).fetchone()[0],
    'prescriptions': conn.execute(text('SELECT COUNT(*) FROM prescription_records')).fetchone()[0],
}

assert sqlite_counts == pg_counts, f"Count mismatch: {sqlite_counts} != {pg_counts}"
print("✅ All counts verified!")
```

---

## Lessons Learned

1. **Don't preserve old IDs** - Let PostgreSQL generate new ones and build explicit mappings
2. **Drop & recreate tables** - Ensures schema perfectly matches current models
3. **Migrate in dependency order** - Parents before children, relationships last
4. **Use context managers** - `with engine.begin() as conn:` handles transactions automatically
5. **Test with production data volume** - Performance characteristics differ significantly at scale
6. **Keep source database read-only** - Prevents changes during migration window
7. **Verify ID mappings** - Print sample mappings to confirm they're being built correctly
8. **Have rollback plan** - Keep SQLite backup until new system fully tested

---

## Related Skills

- `flask-postgresql-system-upgrade` - Overall upgrade strategy for Flask apps
- `legacy-system-safe-refactoring` - General safe refactoring patterns
- `test-driven-development` - Testing migration scripts thoroughly

---

## Troubleshooting

| Error | Cause | Fix |
|-------|-------|-----|
| `KeyError: 0` | Wrong API for `inserted_primary_key` | Use `list(result.inserted_primary_key)[0]` |
| `Foreign key violation` | Inserting relationship before parent | Build ID maps, migrate parents first |
| `Column does not exist` | Model doesn't match target schema | `drop_all()` + `create_all()` |
| `Insufficient privilege` | Can't set replication role | Don't use it, just drop/recreate tables |
| `ModuleNotFoundError` | Path issues with imports | Add backend dir to sys.path |
