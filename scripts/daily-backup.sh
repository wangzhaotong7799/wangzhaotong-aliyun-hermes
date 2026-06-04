#!/bin/bash
# ================================================================
# 每日自动备份脚本 — Hermes 配置 + 技能 + 记忆 → GitHub
# 由 cron 触发，每晚 23:00 运行
# ================================================================
REPO_DIR="/root/wangzhaotong-hermes"
HERMES_HOME="/root/.hermes"
DATE_TAG=$(date +%Y%m%d_%H%M)

cd "$REPO_DIR" || { echo "❌ 无法进入仓库目录 $REPO_DIR"; exit 1; }

# ----- 1. 同步主配置 -----
cp "$HERMES_HOME/config.yaml" "$REPO_DIR/config.yaml"
echo "✅ config.yaml"

# ----- 2. 同步技能（增删同步）-----
rsync -a --delete "$HERMES_HOME/skills/" "$REPO_DIR/skills/"
echo "✅ skills/（增量同步）"

# ----- 3. 同步记忆 -----
mkdir -p "$REPO_DIR/memories"
cp "$HERMES_HOME/memories/MEMORY.md" "$REPO_DIR/memories/MEMORY.md" 2>/dev/null
cp "$HERMES_HOME/memories/USER.md"   "$REPO_DIR/memories/USER.md"   2>/dev/null
echo "✅ memories/"

# ----- 4. 同步 SOUL -----
cp "$HERMES_HOME/SOUL.md" "$REPO_DIR/SOUL.md" 2>/dev/null
echo "✅ SOUL.md"

# ----- 5. 同步网关状态 -----
cp "$HERMES_HOME/gateway_state.json"     "$REPO_DIR/gateway_state.json"     2>/dev/null
cp "$HERMES_HOME/channel_directory.json" "$REPO_DIR/channel_directory.json" 2>/dev/null
echo "✅ gateway_state / channel_directory"

# ----- 6. 带日期标记的配置归档备份 -----
mkdir -p "$REPO_DIR/hermes_config"
cp "$HERMES_HOME/config.yaml" "$REPO_DIR/hermes_config/config_${DATE_TAG}.yaml"
echo "✅ hermes_config/config_${DATE_TAG}.yaml"

# ----- 7. 清理 30 天前的旧配置备份 -----
find "$REPO_DIR/hermes_config" -name 'config_*.yaml' -mtime +30 -delete 2>/dev/null
echo "✅ 已清理 30 天前的旧配置备份"

# ----- 8. 提交并推送 -----
git add -A
if git diff --cached --quiet; then
  echo "ℹ️  没有变更，跳过提交"
else
  git commit -m "🎯 每日自动备份 ${DATE_TAG} : 配置+技能+记忆同步"
  git push origin main 2>&1 || git push origin master 2>&1
  echo "✅ 已推送到 GitHub"
fi
