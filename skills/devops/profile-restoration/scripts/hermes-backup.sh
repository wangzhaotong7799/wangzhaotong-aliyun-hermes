#!/bin/bash
# ===========================================================
# Hermes Agent 配置全量备份脚本
# 用途：每日定时备份 Agent 核心配置，用于系统重装后一键恢复
# 备份路径：/root/hermes-backup/
# 保留策略：保留最近 14 份备份
# ===========================================================
set -euo pipefail

HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
BACKUP_ROOT="/root/hermes-backup"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="hermes-backup-${TIMESTAMP}"
BACKUP_DIR="${BACKUP_ROOT}/${BACKUP_NAME}"
RETENTION_DAYS=14

# 颜色输出
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

info()  { echo -e "${GREEN}[INFO]${NC} $1"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; }

# === 创建备份目录 ===
mkdir -p "${BACKUP_DIR}"
info "备份目录: ${BACKUP_DIR}"

# === 备份 config（配置文件）===
info "备份 config..."
mkdir -p "${BACKUP_DIR}/config"
cp -p "${HERMES_HOME}/config.yaml"           "${BACKUP_DIR}/config/" 2>/dev/null || warn "config.yaml 不存在"
cp -p "${HERMES_HOME}/.env"                   "${BACKUP_DIR}/config/" 2>/dev/null || warn ".env 不存在"
cp -p "${HERMES_HOME}/auth.json"             "${BACKUP_DIR}/config/" 2>/dev/null || warn "auth.json 不存在"
cp -p "${HERMES_HOME}/channel_directory.json" "${BACKUP_DIR}/config/" 2>/dev/null || warn "channel_directory.json 不存在"
cp -p "${HERMES_HOME}/gateway_state.json"    "${BACKUP_DIR}/config/" 2>/dev/null || warn "gateway_state.json 不存在"

# === 备份 SOUL（核心配置/人格）===
info "备份 SOUL..."
mkdir -p "${BACKUP_DIR}/soul"
cp -p "${HERMES_HOME}/SOUL.md" "${BACKUP_DIR}/soul/" 2>/dev/null || warn "SOUL.md 不存在"

# === 备份 skills（技能库，排除 .archive 历史存档）===
info "备份 skills..."
mkdir -p "${BACKUP_DIR}/skills"
if [ -d "${HERMES_HOME}/skills" ]; then
  rsync -a --exclude='.archive' --exclude='__pycache__' --exclude='node_modules' \
    "${HERMES_HOME}/skills/" "${BACKUP_DIR}/skills/"
fi

# === 备份 memories（记忆数据）===
info "备份 memories..."
mkdir -p "${BACKUP_DIR}/memories"
cp -p "${HERMES_HOME}/memories/MEMORY.md" "${BACKUP_DIR}/memories/" 2>/dev/null || warn "MEMORY.md 不存在"
cp -p "${HERMES_HOME}/memories/USER.md"   "${BACKUP_DIR}/memories/" 2>/dev/null || warn "USER.md 不存在"
cp -p "${HERMES_HOME}/memory_store.db"     "${BACKUP_DIR}/memories/" 2>/dev/null || warn "memory_store.db 不存在"

# === 备份 cron（定时任务）===
info "备份 cron..."
mkdir -p "${BACKUP_DIR}/cron"
if [ -d "${HERMES_HOME}/cron" ]; then
  rsync -a "${HERMES_HOME}/cron/" "${BACKUP_DIR}/cron/" --exclude='output/*.md'
fi

# === 备份 kanban（任务看板）===
mkdir -p "${BACKUP_DIR}/kanban"
cp -p "${HERMES_HOME}/kanban.db" "${BACKUP_DIR}/kanban/" 2>/dev/null || warn "kanban.db 不存在"

# === 生成备份清单 ===
{
  echo "Hermes Agent 配置备份: ${TIMESTAMP}"
  echo "================================"
  echo ""
  echo "备份内容清单:"
  echo "- config/           : 主配置、API密钥、认证、频道映射、网关状态"
  echo "- soul/             : 核心人格文件 (SOUL.md)"
  echo "- skills/           : 技能库（排除 .archive）"
  echo "- memories/         : 长期记忆 (MEMORY/USER + memory_store.db)"
  echo "- cron/             : 定时任务定义 (jobs.json)"
  echo "- kanban/           : 看板数据"
  echo ""
  echo "各目录大小:"
  du -sh "${BACKUP_DIR}"/*/ 2>/dev/null | while read line; do echo "  $line"; done
  echo ""
  echo "总大小: $(du -sh "${BACKUP_DIR}" | awk '{print $1}')"
} > "${BACKUP_DIR}/manifest.txt"

# === 打包压缩 ===
info "打包压缩..."
cd "${BACKUP_ROOT}"
tar -czf "${BACKUP_NAME}.tar.gz" "${BACKUP_NAME}" 2>/dev/null
rm -rf "${BACKUP_NAME}"
info "生成压缩包: ${BACKUP_NAME}.tar.gz ($(du -h "${BACKUP_NAME}.tar.gz" | awk '{print $1}'))"

# === 清理过期备份 ===
info "清理超过 ${RETENTION_DAYS} 天的旧备份..."
find "${BACKUP_ROOT}" -name 'hermes-backup-*.tar.gz' -mtime +${RETENTION_DAYS} -delete

# === 统计 ===
TOTAL=$(ls -1 "${BACKUP_ROOT}"/hermes-backup-*.tar.gz 2>/dev/null | wc -l)
LATEST=$(ls -t "${BACKUP_ROOT}"/hermes-backup-*.tar.gz 2>/dev/null | head -1)
LATEST_SIZE=$(du -h "${LATEST}" 2>/dev/null | awk '{print $1}')
info "完成！当前共 ${TOTAL} 份备份，最新: ${LATEST_SIZE}"
