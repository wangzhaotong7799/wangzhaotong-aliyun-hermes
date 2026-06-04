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

## 替代方案：Cron 定时备份（无需 Flask API）

如果需要**纯系统级定时备份**（不依赖 Flask 应用），可用 shell 脚本 + crontab 替代 API 方案。

### 备份脚本模板

```bash
#!/bin/bash
# /root/scripts/backup_db.sh
BACKUP_DIR="/root/db_backups"
DB_NAME="gaofang_v2"
DB_USER="gaofang_app"
DB_PASS="your_password"
DB_HOST="localhost"
RETENTION_DAYS=15

mkdir -p "$BACKUP_DIR"
FILENAME="${DB_NAME}_$(date +%Y%m%d).sql"

PGPASSWORD="$DB_PASS" pg_dump -h "$DB_HOST" -U "$DB_USER" "$DB_NAME" \
  > "${BACKUP_DIR}/${FILENAME}" 2>> "${BACKUP_DIR}/backup.log"

# 清理过期备份
find "$BACKUP_DIR" -name "${DB_NAME}_*.sql" -mtime +${RETENTION_DAYS} -delete
```

### 设置 Cron（每天凌晨 3:00）

```bash
chmod +x /root/scripts/backup_db.sh
echo "0 3 * * * /root/scripts/backup_db.sh" >> /tmp/cron_new
crontab /tmp/cron_new
```

### 优势
- 不依赖 Flask 应用存活
- 资源占用极低（1MB 级备份秒完成）
- 保留策略清晰（`-mtime +N` 控制天数）
- 可叠加到已有 crontab 中

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
