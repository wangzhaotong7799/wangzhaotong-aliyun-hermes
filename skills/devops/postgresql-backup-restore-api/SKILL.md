---
name: postgresql-backup-restore-api
title: PostgreSQL 备份恢复 API 实现（Flask + pg_dump/psql）
description: 在 Flask Web 应用中实现 PostgreSQL 数据库的备份（pg_dump）和恢复（psql）功能，包括 API 端点、备份文件管理和完整闭环测试
category: devops
tags: [postgresql, backup, restore, flask, api, pg_dump]
---

## 适用场景
- Flask 应用需要将 SQLite 备份恢复升级为 PostgreSQL 版本
- Web 界面通过 API 触发数据库备份/恢复
- 需要自动化备份管理（列表、按文件名恢复）

## 架构设计

### 备份文件格式
- **纯 SQL + gzip 压缩**（`.sql.gz`），而非 PostgreSQL custom format
- 通过 `psql` 直接恢复，兼容性最高

### 文件结构
```
project/
├── backup_db.py          # 备份/恢复核心逻辑（独立模块）
├── app.py                # Flask API 路由
├── backups/              # 备份文件目录
└── .env                  # 数据库连接配置
```

## 核心实现要点

### backup_db.py 关键设计

1. **独立加载 .env** — 模块顶部调用 `load_dotenv()`，确保被 `import` 时也能读到配置
2. **PGPASSWORD 显式传递** — 创建 `_get_env()` 辅助函数，每次 `subprocess.run()` 都传入
3. **pg_dump 参数** — 使用 `--no-owner --no-acl` 避免目标环境的角色/权限不匹配
4. **恢复时先 DROP 再重建** — 而非 TRUNCATE，避免 CREATE TABLE 冲突

### 恢复策略：DROP 优于 TRUNCATE

```python
# ❌ 错误做法：TRUNCATE CASCADE 保留表结构
# pg_dump 的 SQL 包含 CREATE TABLE，和已有表冲突

# ✅ 正确做法：先 DROP 所有表（CASCADE 删除外键依赖）
# pg_dump 的 SQL 成功重建全部表和数据
for table in ['table_a', 'table_b', ...]:
    subprocess.run(['psql', '-c', f'DROP TABLE IF EXISTS {table} CASCADE;'], ...)
```

### Python 3.6 兼容性
- `subprocess.run()` 不支持 `capture_output=` 参数（3.7+），改用 `stdout=subprocess.PIPE, stderr=subprocess.PIPE`
- 所有 subprocess 调用需显式设置 `timeout=` 防止挂起

## 验证清单

恢复后必须检查中间表的数据完整性（最容易遗漏）：
```sql
SELECT relname, n_live_tup FROM pg_stat_user_tables ORDER BY relname;
```
重点关注 `user_roles`、`role_permissions` 等关联表的记录数是否 > 0。

## 测试流程

### API 流程（用户表存在时）
```bash
curl -X POST /api/backup                    # 备份
curl GET /api/backups                       # 查看列表
curl -X POST /api/restore -d '{"file":"..."}'  # 恢复
```

### 命令行兜底（用户表清空后——管理员 Token 不可用时）
```bash
gunzip -c backups/backup.sql.gz | psql -U user -d dbname
```
