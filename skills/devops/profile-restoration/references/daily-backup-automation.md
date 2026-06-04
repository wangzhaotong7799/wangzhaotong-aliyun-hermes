# 每日自动备份到 GitHub

Hermes 状态（配置 + 技能 + 记忆 + SOUL）自动同步到 GitHub 仓库的完整方案。

## 适用场景

用户要求「每天晚上23点自动把所有的配置记忆推送到 GitHub 专属仓库」。

## 脚本结构

```bash
#!/bin/bash
# daily-backup.sh — Hermes 每日状态同步到 GitHub 仓库

REPO_DIR="/root/wangzhaotong-hermes"           # 仓库本地路径
HERMES_HOME="/root/.hermes"                    # Hermes 主目录
DATE_TAG=$(date +%Y%m%d_%H%M)

cd "$REPO_DIR" || exit 1

# 1. 同步主配置
cp "$HERMES_HOME/config.yaml" "$REPO_DIR/config.yaml"

# 2. 同步技能（增删同步）
rsync -a --delete "$HERMES_HOME/skills/" "$REPO_DIR/skills/"

# 3. 同步记忆
mkdir -p "$REPO_DIR/memories"
cp "$HERMES_HOME/memories/MEMORY.md" "$REPO_DIR/memories/MEMORY.md" 2>/dev/null
cp "$HERMES_HOME/memories/USER.md"   "$REPO_DIR/memories/USER.md"   2>/dev/null

# 4. 同步 SOUL
cp "$HERMES_HOME/SOUL.md" "$REPO_DIR/SOUL.md" 2>/dev/null

# 5. 同步网关状态
cp "$HERMES_HOME/gateway_state.json"     "$REPO_DIR/gateway_state.json"     2>/dev/null
cp "$HERMES_HOME/channel_directory.json" "$REPO_DIR/channel_directory.json" 2>/dev/null

# 6. 带日期标记的配置归档备份（保留最近30天）
mkdir -p "$REPO_DIR/hermes_config"
cp "$HERMES_HOME/config.yaml" "$REPO_DIR/hermes_config/config_${DATE_TAG}.yaml"
find "$REPO_DIR/hermes_config" -name 'config_*.yaml' -mtime +30 -delete

# 7. 提交并推送
git add -A
git diff --cached --quiet || (git commit -m "🎯 每日自动备份 ${DATE_TAG} : 配置+技能+记忆同步" && git push)
```

## Cron 配置

使用 Hermes 内置 cron 工具创建定时任务：

```bash
# 方法 A：用 hermes cron create
hermes cron create \
  --schedule "0 23 * * *" \
  --name "每日备份到GitHub" \
  --script /root/wangzhaotong-hermes/scripts/daily-backup.sh
```

```bash
# 方法 B：用系统 crontab
echo "0 23 * * * /root/wangzhaotong-hermes/scripts/daily-backup.sh" | crontab -
```

## 关键要点

### .gitignore 配置

| 排除项 | 原因 |
|--------|------|
| `.env`, `auth.json` | API 密钥和认证凭据，绝不上传 |
| `sessions/` | 历史对话记录，不需要同步 |
| `checkpoints/` | 文件系统检查点 |
| `state.db*`, `kanban.db` | 运行时数据库，每台机器自动生成 |
| `logs/`, `cache/`, `images/` | 缓存和日志 |
| `*.mp3`, `*.mp4`, `*.wav`, `*.zip`, `*.jpg`, `*.png` | 大文件，不应进 git |
| `horror-pipeline/`, `videos/` | 音视频素材目录 |

### 需要同步的内容

| 内容 | 位置 | 说明 |
|------|------|------|
| `config.yaml` | repo 根目录 | Hermes 主配置 |
| `skills/` | repo skills/ | 所有自定义技能（rsync --delete 保持同步） |
| `memories/MEMORY.md` | repo memories/ | Agent 记忆 |
| `memories/USER.md` | repo memories/ | 用户画像记忆 |
| `SOUL.md` | repo 根目录 | Agent 人格文件 |
| `gateway_state.json` | repo 根目录 | 消息平台连接状态 |
| `channel_directory.json` | repo 根目录 | 频道映射表 |
| `hermes_config/config_*.yaml` | 归档目录 | 带日期的主配置备份 |

## 常见陷阱

1. **大文件阻塞推送**：首次同步时，`rsync --delete` 可能会将音视频大文件也带入仓库（如 `horror-pipeline/audio/*.mp3`），导致 `git push` 超时。解决方案：
   - 在 `.gitignore` 中添加 `*.mp3 *.mp4 *.wav` 等文件类型
   - 用 `git rm --cached` 移除已跟踪的大文件
   - 修正提交后重新推送

2. **SSH 连接超时**：如果仓库在网络慢时推送超时，脚本中的 `git push` 可能失败。建议给 `git push` 加更长超时或放到后台执行。

3. **首推大量文件**：当服务器上的技能库远大于仓库中已有的（如 Hermes 版本升级后新增了大量内置技能），首次推送会有几百个文件变更。耐心等待即可。

4. **记忆是否进 gitignore**：`memories/` 默认在 Hermes 仓库的 `.gitignore` 中（标注"不需要同步历史聊天记录"）。如果要同步记忆，需要手动从 `.gitignore` 中移除 `memories/` 这一行。
