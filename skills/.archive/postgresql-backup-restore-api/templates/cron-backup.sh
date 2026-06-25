#!/bin/bash
# =====================================================
# PostgreSQL 每日自动备份脚本模板
# 用法: 复制修改后 chmod +x, 添加到 crontab
# =====================================================

BACKUP_DIR="/root/db_backups"
DB_NAME="your_database"
DB_USER="your_user"
DB_PASS="your_password"
DB_HOST="localhost"
RETENTION_DAYS=15

mkdir -p "$BACKUP_DIR"
FILENAME="${DB_NAME}_$(date +%Y%m%d).sql"
FILEPATH="${BACKUP_DIR}/${FILENAME}"

# 执行备份
PGPASSWORD="$DB_PASS" pg_dump -h "$DB_HOST" -U "$DB_USER" "$DB_NAME" \
  > "$FILEPATH" 2>> "${BACKUP_DIR}/backup.log"

if [ $? -eq 0 ] && [ -s "$FILEPATH" ]; then
    SIZE=$(du -h "$FILEPATH" | cut -f1)
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ✅ 备份成功: ${FILENAME} (${SIZE})" \
      >> "${BACKUP_DIR}/backup.log"
else
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ❌ 备份失败: ${FILENAME}" \
      >> "${BACKUP_DIR}/backup.log"
    rm -f "$FILEPATH"
    exit 1
fi

# 清理超过保留天数的旧备份
find "$BACKUP_DIR" -name "${DB_NAME}_*.sql" -type f -mtime +${RETENTION_DAYS} \
  -delete >> "${BACKUP_DIR}/backup.log" 2>/dev/null

exit 0
