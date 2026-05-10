---
name: token-manager
description: "Token管家 — 每日 Token 用量统计（TokScale）+ Token 压缩（RTK）一体化管理"
version: 1.0.0
author: Hermes Agent
metadata:
  hermes:
    tags: [token, usage, stats, compression, rtk, tokscale, daily-report]
---

# Token管家 — 每日用量统计 + Token 压缩

## 概述

集成了两大 Token 管理利器：
1. **TokScale** — 每日 Token 用量统计（按日期/模型/客户端明细）
2. **RTK** — 终端输出压缩（平均节省 80% Token）

---

## 🔄 多智能体安装

**另一个智能体只需读取此文件即可自行安装** — 不需要人类解释步骤。

1. 读取本文件的全部内容
2. 按「前置安装」章节执行安装命令
3. 按「配置检查」验证是否就绪
4. 按「每日自动报告」配置 cron 定时任务（可选）

### 前置安装

在其他 Agent 上使用此技能前，需先安装：

```bash
# 1. 安装 TokScale
npm install -g @tokscale/cli

# 2. 安装 RTK 二进制
wget -q -O /tmp/rtk.tar.gz https://github.com/rtk-ai/rtk/releases/latest/download/rtk-x86_64-unknown-linux-musl.tar.gz
tar xzf /tmp/rtk.tar.gz -C /usr/local/bin/ rtk && chmod +x /usr/local/bin/rtk

# 3. 安装 rtk-hermes 插件到 Hermes Python 环境
"$(dirname "$(which hermes)")/python" -m pip install rtk-hermes

# 4. 在 config.yaml 中启用插件（plugins.enabled 下添加 rtk-rewrite）

# 5. 安装全局 Hook（使所有终端命令自动走压缩通道）
rtk init -g --auto-patch
```

---

## 当前状态（本机参考数据）

| 组件 | 路径/版本 | 状态 |
|------|-----------|------|
| **TokScale** | `/root/.hermes/node/bin/tokscale` v2.1.0 | ✅ 可用 |
| **RTK** | `/usr/local/bin/rtk` v0.38.0 | ✅ 可用 |
| **rtk-hermes 插件** | Hermes `config.yaml` 已注册 `rtk-rewrite` | ✅ 已配置 |
| **RTK 全局 Hook** | `rtk hook claude` + `settings.json` | ✅ 已安装 |
| **累计节约** | 181.4K tokens (80.9%) / 206 commands | ✅ 运行中 |

---

## 📊 一、每日 Token 用量统计

### 1.1 查询今日用量

```bash
/root/.hermes/node/bin/tokscale graph --client hermes --today
```

### 1.2 查询指定日期范围（逐日明细）

```bash
# 最近一周
/root/.hermes/node/bin/tokscale graph --client hermes --week

# 自定义范围
/root/.hermes/node/bin/tokscale graph --client hermes --since 2026-05-01 --until 2026-05-07

# 本月
/root/.hermes/node/bin/tokscale graph --client hermes --month
```

### 1.3 汇总报表

```bash
# 按模型汇总
/root/.hermes/node/bin/tokscale models --client hermes --light

# 按月汇总
/root/.hermes/node/bin/tokscale monthly --client hermes --light

# TUI 交互界面
/root/.hermes/node/bin/tokscale tui --client hermes
```

### 1.4 输出说明

`tokscale graph` 返回 JSON 格式，每日一条：

```json
{
  "date": "2026-05-06",
  "totals": {
    "tokens": 22715775,      // Token总量（含缓存）
    "cost": 0.1962,          // 费用（美元）
    "messages": 80           // 消息数
  },
  "tokenBreakdown": {
    "input": 789699,         // 输入 Token
    "output": 87484,         // 输出 Token
    "cacheRead": 21838592,   // 缓存命中（免费）
    "cacheWrite": 0,         // 缓存写入
    "reasoning": 0           // 推理 Token
  }
}
```

---

## 🔧 二、Token 压缩（RTK）

### 2.1 查看压缩收益

```bash
rtk gain
```

输出示例：
```
Total commands:    206
Input tokens:      224.3K
Output tokens:     43.0K
Tokens saved:      181.4K (80.9%)
Efficiency meter: ███████████████████░░░░░ 80.9%
```

### 2.2 支持的自动压缩规则

`rtk-hermes` 插件的 `rtk rewrite` 会自动将以下命令转为压缩版本：

| 原始命令 | 压缩为 | 压缩率 |
|---------|--------|--------|
| `git status/diff/log` | `rtk git ...` | 60-80% |
| `cat file.py` | `rtk read file.py` | 80%+ |
| `ps aux` | `rtk:toml ps aux` | 83% |
| `curl http://...` | `rtk curl http://...` | 90%+ |
| `grep -r pattern` | `rtk grep pattern` | 40% |
| `find /path -name x` | `rtk find /path -name x` | 60% |
| `df -h` | `rtk df -h` | 50% |
| `ls -la` | `rtk ls -la` | 40% |
| `npm test` | 无需压缩 | - |

### 2.3 Hermes 集成原理

- `rtk-hermes` 插件（v1.2.1）拦截所有 `terminal()` 工具调用
- 在执行前通过 `rtk rewrite <command>` 尝试重写
- **失败降级**：如果 RTK 不可用或无法重写，直接执行原命令（fail-open）
- 超时 2 秒，不会阻塞工作流

### 2.4 手动使用 RTK

当需要强制压缩输出时，直接使用 RTK 命令：

```bash
rtk git status           # 压缩版 git status
rtk read /path/to/file   # 压缩版 cat
rtk grep "pattern" *.py  # 压缩版 grep
rtk curl https://api.x   # 压缩版 curl
rtk ls -la /tmp          # 压缩版 ls
rtk ps aux               # 压缩版 ps aux
rtk df -h                # 压缩版 df -h
```

### 2.5 配置检查

```bash
# 检查 RTK 状态
rtk init --show

# 检查 Hermes 插件注册
grep "rtk-rewrite" /root/.hermes/config.yaml

# 检查本地 Hook
cat /root/.claude/settings.json
```

---

## 📋 三、快速用法速查

```bash
# === 用量统计 ===
tokscale graph --client hermes --today        # 今日用量
tokscale graph --client hermes --week          # 本周逐日
tokscale graph --client hermes --since X --until Y  # 自定义区间
tokscale models --client hermes --light        # 按模型汇总
tokscale monthly --client hermes --light       # 按月汇总
tokscale tui --client hermes                   # 交互界面

# === Token 压缩 ===
rtk gain                                       # 查看节约统计

# === 路径 ===
TOKSCALE=/root/.hermes/node/bin/tokscale
RTK=/usr/local/bin/rtk
```

## ⚠️ 注意事项

- **TokScale 路径**：安装在 `/root/.hermes/node/bin/tokscale`，不在全局 PATH 中
- **rtk-hermes 插件**：修改 `config.yaml` 后需重启 Hermes Gateway 才生效
- **RTK 超时**：插件默认 2 秒超时，不会阻塞正常命令执行
- **缓存命中率高**：DeepSeek 等提供商缓存命中率约 96%，实际净 Token 消耗远低于总量
- **费用极低**：5 月累计 $4.99（约 35 元人民币），日均约 $0.17

---

## ⏰ 四、每日自动报告（Cron 定时任务）

### 4.1 Token 日报（每日 08:00）

此技能已在本机配置了每日 08:00 的 cron 任务，自动生成前一日 Token 报告。

**Cron 任务配置参考**（供其他 Agent 参考使用）：

```yaml
# Job 名称: 每日Token用量报告
# 执行时间: 0 8 * * *（每天早上8点）
# 加载技能: devops/token-manager
# 投递方式: 自动输出到终端（由 cron 框架投递给用户）
```

**Cron 任务 Prompt 模板：**

```
任务：生成昨日 Token 使用和节约情况报告

1. 计算昨天的日期（YYYY-MM-DD格式）
2. 用以下命令查询昨日 TokScale 用量明细：
   /root/.hermes/node/bin/tokscale graph --client hermes --since {昨天日期} --until {昨天日期}
3. 用以下命令查询 RTK 压缩节约统计：
   rtk gain
4. 组装含以下内容的报告输出到终端（自动投递）：
   - 消息数 / Token总量（输入+输出+缓存）/ 费用
   - 累计压缩率 / 已省 tokens
   - 本月累计
5. 如果 TokScale 或 RTK 返回错误，如实报告不编造
```

### 4.2 报告示例输出

```
📊 Token 日报 · 2026-05-07

━━━━ 用量统计 ━━━━
• 消息数：80 条
• Token 总量：22.7M (输入 789K + 输出 87K + 缓存 21.8M)
• 费用：$0.20

━━━━ 压缩节约 ━━━━
• 累计压缩：80.9% (已省 181K tokens)
• 昨日命令数：6 条

━━━━ 综合 ━━━━
• 本月累计：$4.99
• 缓存命中率：约 96%
```

### 4.3 配套脚本

本技能附带一个 `scripts/daily-token-report.sh` 脚本，可以直接作为 `cron` 任务执行：

```bash
# 手动执行查看
~/.hermes/skills/devops/token-manager/scripts/daily-token-report.sh
```

---

## 📂 五、文件位置（供其他智能体读取）

本技能的 SKILL.md 已推送到 GitHub：

```
https://github.com/wangzhaotong7799/wangzhaotong-aliyun-hermes/blob/main/skills/token-manager.SKILL.md
```

其他智能体直接读取此文件即可获得完整安装和使用说明。
