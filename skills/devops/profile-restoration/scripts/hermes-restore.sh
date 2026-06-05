#!/bin/bash
# ===========================================================
# Hermes Agent 配置恢复脚本
# 用途：从备份压缩包一键恢复所有配置
# 用法：bash hermes-restore.sh [备份文件名]
#       不传参数则列出可用备份供选择
# ===========================================================
set -euo pipefail

HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
BACKUP_ROOT="/root/hermes-backup"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

info()  { echo -e "${GREEN}[INFO]${NC} $1"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; }
hl()    { echo -e "${CYAN}$1${NC}"; }

list_backups() {
  echo "可用的备份文件:"
  echo ""
  local i=1
  while IFS= read -r file; do
    local name=$(basename "$file" .tar.gz | sed 's/hermes-backup-//')
    local size=$(du -h "$file" | awk '{print $1}')
    local date=$(date -r "$file" "+%Y-%m-%d %H:%M:%S")
    echo "  [$i] ${name}  (${size}, ${date})"
    i=$((i + 1))
  done < <(ls -t "${BACKUP_ROOT}"/hermes-backup-*.tar.gz 2>/dev/null)
  if [ "$i" -eq 1 ]; then
    error "没有找到备份文件"
    exit 1
  fi
  echo ""
  read -p "输入编号选择要恢复的备份: " choice
  local selected=$(ls -t "${BACKUP_ROOT}"/hermes-backup-*.tar.gz 2>/dev/null | sed -n "${choice}p")
  if [ -z "$selected" ]; then
    error "无效选择"
    exit 1
  fi
  RESTORE_FILE="$selected"
}

if [ $# -eq 0 ]; then
  list_backups
else
  RESTORE_FILE="$1"
  if [ ! -f "$RESTORE_FILE" ]; then
    RESTORE_FILE="${BACKUP_ROOT}/$1"
    if [ ! -f "$RESTORE_FILE" ]; then
      RESTORE_FILE="${BACKUP_ROOT}/$1.tar.gz"
      if [ ! -f "$RESTORE_FILE" ]; then
        error "备份文件不存在: $1"
        echo ""
        ls -1 "${BACKUP_ROOT}"/hermes-backup-*.tar.gz 2>/dev/null || echo "  (无)"
        exit 1
      fi
    fi
  fi
fi

echo ""; hl "═══════════════════════════════════════"; hl "  Hermes Agent 配置恢复"; hl "═══════════════════════════════════════"; echo ""
info "备份文件: ${RESTORE_FILE}"
info "目标目录: ${HERMES_HOME}"; echo ""

echo -e "${YELLOW}⚠  警告：恢复操作将覆盖以下现有文件：${NC}"
echo "  - config.yaml, .env, auth.json, channel_directory.json"
echo "  - SOUL.md, skills/, memories/ + memory_store.db"
echo "  - cron/ (定时任务), kanban.db"
echo ""
read -p "确认恢复? (yes/no): " CONFIRM
if [ "$CONFIRM" != "yes" ]; then info "已取消"; exit 0; fi

TMP_DIR=$(mktemp -d); trap "rm -rf ${TMP_DIR}" EXIT
info "解压备份文件..."
tar -xzf "${RESTORE_FILE}" -C "${TMP_DIR}"
EXTRACTED_DIR=$(find "${TMP_DIR}" -mindepth 1 -maxdepth 1 -type d | head -1)
if [ -z "$EXTRACTED_DIR" ]; then error "解压失败"; exit 1; fi

info "恢复 config..."; cp -f "${EXTRACTED_DIR}/config/config.yaml" "${HERMES_HOME}/config.yaml" 2>/dev/null || warn "config.yaml 不存在"
cp -f "${EXTRACTED_DIR}/config/.env" "${HERMES_HOME}/.env" 2>/dev/null || warn ".env 不存在"
cp -f "${EXTRACTED_DIR}/config/auth.json" "${HERMES_HOME}/auth.json" 2>/dev/null || warn "auth.json 不存在"
cp -f "${EXTRACTED_DIR}/config/channel_directory.json" "${HERMES_HOME}/channel_directory.json" 2>/dev/null || warn "channel_directory.json 不存在"
cp -f "${EXTRACTED_DIR}/config/gateway_state.json" "${HERMES_HOME}/gateway_state.json" 2>/dev/null || warn "gateway_state.json 不存在"

info "恢复 SOUL..."; cp -f "${EXTRACTED_DIR}/soul/SOUL.md" "${HERMES_HOME}/SOUL.md" 2>/dev/null || warn "SOUL.md 不存在"

info "恢复 skills..."; if [ -d "${EXTRACTED_DIR}/skills" ]; then rm -rf "${HERMES_HOME}/skills"; cp -a "${EXTRACTED_DIR}/skills" "${HERMES_HOME}/skills"; fi

info "恢复 memories..."; cp -f "${EXTRACTED_DIR}/memories/MEMORY.md" "${HERMES_HOME}/memories/MEMORY.md" 2>/dev/null || warn "MEMORY.md 不存在"
cp -f "${EXTRACTED_DIR}/memories/USER.md" "${HERMES_HOME}/memories/USER.md" 2>/dev/null || warn "USER.md 不存在"
cp -f "${EXTRACTED_DIR}/memories/memory_store.db" "${HERMES_HOME}/memory_store.db" 2>/dev/null || warn "memory_store.db 不存在"

info "恢复 cron..."; cp -f "${EXTRACTED_DIR}/cron/jobs.json" "${HERMES_HOME}/cron/jobs.json" 2>/dev/null || warn "cron/jobs.json 不存在"
info "恢复 kanban..."; cp -f "${EXTRACTED_DIR}/kanban/kanban.db" "${HERMES_HOME}/kanban.db" 2>/dev/null || warn "kanban.db 不存在"

chmod 600 "${HERMES_HOME}/.env" "${HERMES_HOME}/auth.json" 2>/dev/null || true

echo ""; hl "═══════════════════════════════════════"; hl "  恢复完成！"; hl "═══════════════════════════════════════"; echo ""
info "建议重启 Hermes 使配置生效：hermes gateway restart 或 systemctl --user restart hermes"
