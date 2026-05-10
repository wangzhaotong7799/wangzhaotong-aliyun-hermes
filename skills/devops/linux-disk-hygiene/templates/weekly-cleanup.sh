#!/bin/bash
# =====================================================
# 每周自动清理脚本模板
# 使用: 修改 CLEANUP_PATTERNS 和阈值后部署到 crontab
# 路径模板: /root/scripts/weekly_cleanup.sh
# =====================================================

LOG_FILE="/root/scripts/weekly_cleanup.log"

echo "===== $(date '+%Y-%m-%d %H:%M:%S') 开始清理 =====" >> "$LOG_FILE"

# ==== 配置区（按需修改）====
BACKUP_DIR="/root/db_backups"           # 日常备份目录（跳过）
PIP_CACHE_THRESHOLD=51200               # pip 缓存阈值（KB）
TEMP_FILE_DAYS=7                        # 临时文件保留天数
# ==========================

# ==== 清理函数 ====
clean_glob() {
    local pattern="$1"
    local desc="$2"
    if ls $pattern 2>/dev/null | grep -q .; then
        local size
        size=$(du -sch $pattern 2>/dev/null | tail -1 | awk '{print $1}')
        rm -rf $pattern 2>/dev/null
        echo "  ✅ 已清理: $desc ($size)" >> "$LOG_FILE"
    else
        echo "  ⏭️  无: $desc" >> "$LOG_FILE"
    fi
}

# ==== Tier 1 安全清理 ====
clean_glob "/root/hermes_conversation_*.json" "Hermes 旧对话导出"
clean_glob "/root/hermes_main_backup_*.py" "Hermes 旧备份脚本"
clean_glob "/root/hermes_env_backup_*.txt" "Hermes 旧环境备份"
clean_glob "/root/hermes_config_backup_*.yaml" "Hermes 旧配置备份"
clean_glob "/root/install_panel.sh" "宝塔安装脚本"

# /root 下的冗余 SQL（排除日常备份目录中的文件）
for f in /root/*.sql; do
    [ -f "$f" ] || continue
    [[ "$f" == /root/gaofang_v2_*.sql ]] && continue
    size=$(du -h "$f" 2>/dev/null | cut -f1)
    rm -f "$f"
    echo "  ✅ 已清理: 冗余SQL $(basename "$f") ($size)" >> "$LOG_FILE"
done

# npm 缓存
if [ -d /root/.npm ] && [ "$(du -s /root/.npm 2>/dev/null | awk '{print $1}')" -gt 10 ]; then
    npm cache clean --force 2>/dev/null
    rm -rf /root/.npm/_cacache 2>/dev/null
    echo "  ✅ 已清理: npm 缓存" >> "$LOG_FILE"
fi

# pip 缓存（超过阈值才清）
PIP_SIZE=$(du -s /root/.cache/pip 2>/dev/null | awk '{print $1}')
if [ "$PIP_SIZE" -gt "$PIP_CACHE_THRESHOLD" ] 2>/dev/null; then
    rm -rf /root/.cache/pip/*
    echo "  ✅ 已清理: pip 缓存 (超过 ${PIP_CACHE_THRESHOLD}KB)" >> "$LOG_FILE"
fi

# 临时文件
find /tmp -maxdepth 1 -type f \( -name "*.tmp" -o -name "*.log" \) -mtime +${TEMP_FILE_DAYS} 2>/dev/null | head -50 | while read f; do
    rm -f "$f"
    echo "  ✅ 已清理: 临时文件 $(basename "$f")" >> "$LOG_FILE"
done

echo "===== $(date '+%Y-%m-%d %H:%M:%S') 清理完成 =====" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"

# 保留最近 50 行日志
tail -n 50 "$LOG_FILE" > "${LOG_FILE}.tmp" && mv "${LOG_FILE}.tmp" "$LOG_FILE"
