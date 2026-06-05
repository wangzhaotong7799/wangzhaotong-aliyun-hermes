# 本地 Tarball 全量备份方案

与 GitHub 同步（轻量配置同步）互补的**本地全量备份**方案。备份内容包括运行时数据库（memory_store.db, state.db, kanban.db）等 git 不跟踪的数据。

## 适用场景

- 系统重装后**一键恢复**所有配置 + 数据
- 补充 GitHub 同步（git 不存 secrets 和运行时 DB）
- 离线恢复场景（无需网络）

## 结构总览

```
备份目录: /root/hermes-backup/
备份脚本: /root/.hermes/scripts/hermes-backup.sh
恢复脚本: /root/.hermes/scripts/hermes-restore.sh
定时任务: 每日 02:00 (系统 crontab)
保留策略: 最近 14 份
```

## 备份内容

| 模块 | 包含文件 | 说明 |
|------|----------|------|
| config | config.yaml, .env, auth.json, channel_directory.json, gateway_state.json | 主配置 + 凭据 + 频道映射 |
| soul | SOUL.md | 核心人格文件 |
| skills | 完整技能库（排除 .archive） | 1450+ 文件，~11MB 压缩 |
| memories | MEMORY.md, USER.md, memory_store.db | 长期记忆文本 + 持久化 DB |
| cron | jobs.json + 历史输出 | 定时任务定义 |
| kanban | kanban.db | 看板任务数据 |

## 备份脚本 (`hermes-backup.sh`)

```bash
#!/bin/bash
HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
BACKUP_ROOT="/root/hermes-backup"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="hermes-backup-${TIMESTAMP}"
BACKUP_DIR="${BACKUP_ROOT}/${BACKUP_NAME}"
RETENTION_DAYS=14

# 1. 逐模块复制到临时目录
cp -p "${HERMES_HOME}/config.yaml"  "${BACKUP_DIR}/config/"
cp -p "${HERMES_HOME}/.env"         "${BACKUP_DIR}/config/"
cp -p "${HERMES_HOME}/SOUL.md"      "${BACKUP_DIR}/soul/"
rsync -a --exclude='.archive' "${HERMES_HOME}/skills/" "${BACKUP_DIR}/skills/"
cp -p "${HERMES_HOME}/memory_store.db"  "${BACKUP_DIR}/memories/"
cp -p "${HERMES_HOME}/cron/jobs.json"   "${BACKUP_DIR}/cron/"

# 2. 打包压缩
cd "${BACKUP_ROOT}"
tar -czf "${BACKUP_NAME}.tar.gz" "${BACKUP_NAME}"
rm -rf "${BACKUP_NAME}"

# 3. 清理过期
find "${BACKUP_ROOT}" -name 'hermes-backup-*.tar.gz' -mtime +14 -delete

# 4. 生成 manifest.txt
```

## 恢复脚本 (`hermes-restore.sh`)

交互式恢复，支持参数传入或列表选择：

```bash
# 列出备份 → 交互选择
bash /root/.hermes/scripts/hermes-restore.sh

# 或直接指定备份文件
bash /root/.hermes/scripts/hermes-restore.sh /root/hermes-backup/hermes-backup-20260605_203000.tar.gz
```

恢复流程：
1. 显示警告并确认（覆盖 config/skills/memories/cron/kanban）
2. 解压到临时目录
3. 逐模块覆盖 `~/.hermes/`
4. 设置 `.env` 和 `auth.json` 权限为 600

## Cron 配置

通过系统 crontab 运行：

```cron
0 2 * * * /root/.hermes/scripts/hermes-backup.sh > /root/hermes-backup/backup-cron.log 2>&1
```

查看执行日志：
```bash
cat /root/hermes-backup/backup-cron.log
ls -lh /root/hermes-backup/  # 查看备份文件列表
```

## 对比：本地 Tarball vs GitHub 同步

| 维度 | 本地 Tarball | GitHub 同步 |
|------|-------------|-------------|
| **备份内容** | 全量（含 secrets + DB） | 仅配置/技能/记忆文本 |
| **存储位置** | 本机磁盘 | GitHub 远程仓库 |
| **恢复能力** | 一键恢复全部 | 需手动补 secrets |
| **增量** | 全量每次 | git 增量 |
| **压缩后大小** | ~11MB | ~22MB（含 git 历史） |
| **保留策略** | 最近 14 份 | git 永久历史 |
| **适用场景** | 系统重装、离线恢复 | 日常版本跟踪、跨机器同步 |

**建议两者并用**：GitHub 同步配置版本历史，本地 Tarball 做全量数据兜底。
