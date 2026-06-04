# ID 重排流程（PostgreSQL）

## 适用场景
- 数据迁移后自增序列落后于已有数据
- 新记录 ID 低于旧数据，导致 `id DESC` 排序紊乱
- 需要 ID 连续无空缺

## 前置确认

```sql
-- 检查外键依赖
SELECT tc.table_name, kcu.column_name, ccu.table_name AS ref_table
FROM information_schema.table_constraints tc
JOIN information_schema.key_column_usage kcu USING (constraint_name, table_schema)
JOIN information_schema.constraint_column_usage ccu USING (constraint_name, table_schema)
WHERE tc.constraint_type = 'FOREIGN KEY' AND ccu.table_name = 'prescription_records';
```
→ 如果返回空行，说明无外键依赖，可直接操作。

## 标准执行脚本

```sql
BEGIN;

-- 1. 先删除主键约束（无外键依赖则安全）
ALTER TABLE prescription_records DROP CONSTRAINT prescription_records_pkey;

-- 2. 按当前 id 顺序重新编号
WITH renumbered AS (
    SELECT id AS old_id, ROW_NUMBER() OVER (ORDER BY id) AS new_id
    FROM prescription_records
)
UPDATE prescription_records t
SET id = r.new_id
FROM renumbered r
WHERE t.id = r.old_id;

-- 3. 重建主键
ALTER TABLE prescription_records ADD PRIMARY KEY (id);

-- 4. 重置自增序列
SELECT setval('prescription_records_id_seq',
    COALESCE((SELECT MAX(id) FROM prescription_records), 1));

COMMIT;
```

## 验证

```sql
-- 确认无空缺
SELECT MIN(id), MAX(id), COUNT(*),
       (MAX(id)-MIN(id)+1) - COUNT(*) AS gaps
FROM prescription_records;

-- 确认序列正确
SELECT last_value, is_called FROM prescription_records_id_seq;
-- last_value 应 = max(id)，下一个 nextval 返回 max(id)+1
```

## 重要注意事项

1. **必须先确认无外键依赖**，否则需级联更新关联表
2. **事务内执行**，失败自动回滚
3. **重启应用进程**（如 gunicorn）清 ORM 缓存
4. 重排后**备份一次数据库**，作为新基线
