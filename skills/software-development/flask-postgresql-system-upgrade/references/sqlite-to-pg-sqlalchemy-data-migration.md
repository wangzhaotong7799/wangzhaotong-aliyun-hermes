# SQLite → PostgreSQL Data Migration with SQLAlchemy

> 吸收自 `sqlite-to-postgresql-migration-with-sqlalchemy`（2026-05 合并）
> 本节覆盖 flask-postgresql-system-upgrade 主文档未详尽展开的数据迁移 SQLAlchemy 细节。

## 核心挑战：自增 ID 冲突

SQLite 和 PostgreSQL 的 AUTOINCREMENT 行为不同。**不要保留旧 ID**，应构建 ID 映射：

```python
old_id_to_new_id = {}
for row in sqlite_cur.fetchall():
    result = conn.execute(Model.__table__.insert().values(**data))
    new_id = list(result.inserted_primary_key)[0]  # SQLAlchemy 1.4 API
    old_id_to_new_id[row['id']] = new_id

# 关联表使用映射后的新 ID
conn.execute(relationship_table.insert().values(
    parent_id=old_id_to_new_id[old_parent_id],
    child_id=old_id_to_new_id[old_child_id]
))
```

## Post-Migration: 序列同步

迁移后 PostgreSQL 序列落后于实际 MAX(id)，导致新记录 ID 比旧数据还小：

```sql
-- 检测：对比序列值与实际最大值
SELECT last_value FROM tablename_id_seq;
SELECT MAX(id) FROM tablename;

-- 修复：按数据量选择策略

-- 策略 A: Fix Sequence Only (gap < 50%)
SELECT setval('tablename_id_seq', (SELECT MAX(id) FROM tablename));

-- 策略 B: Renumber All IDs (gap >= 30%, sorting busted)
-- 先确认无 FK 引用 id 列
UPDATE tablename t
SET id = t2.new_id
FROM (SELECT id, ROW_NUMBER() OVER (ORDER BY id) AS new_id FROM tablename) t2
WHERE t.id = t2.id;
```

### 何时不要重编号
- FK 约束引用 id 列 → 改排序为 `ORDER BY created_at DESC`
- 有其他应用缓存 ID → 保留原始 ID

## 迁移完整示例

见主文档「阶段二：数据迁移」+ 本参考的 SQLAlchemy 插入逻辑。迁移严格按依赖顺序：
1. 无 FK 的表（parent 表）
2. 有 FK 的表（使用 ID 映射）
3. 多对多关联表（最后）

## Python 3.6 兼容版本

| 库 | 兼容版本 |
|---|---|
| Flask | 2.0.3 |
| SQLAlchemy | 1.4.46 |
| psycopg2-binary | 2.9.3 |
| PyJWT | 2.4.0 |
