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

## 前置安装

在其他 Agent 上使用此技能前，需先安装两个工具：

### 安装 TokScale
```bash
npm install -g @tokscale/cli
```

### 安装 RTK + rtk-hermes 插件
```bash
# 1. 安装 RTK 二进制（下载预编译版）
wget -q -O /tmp/rtk.tar.gz https://github.com/rtk-ai/rtk/releases/latest/download/rtk-x86_64-unknown-linux-musl.tar.gz
tar xzf /tmp/rtk.tar.gz -C /usr/local/bin/ rtk
chmod +x /usr/local/bin/rtk

# 2. 安装 rtk-hermes 插件到 Hermes 的 Python 环境
"$(dirname "$(which hermes)")/python" -m pip install rtk-hermes

# 3. 在 config.yaml 中启用插件
# 在 plugins.enabled 下添加 rtk-rewrite

# 4. 安装全局 Hook（可选，用于 Claude Code 或 shell 级拦截）
rtk init -g --auto-patch
```

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
    "tokens": 22715775,
    "cost": 0.1962,
    "messages": 80
  },
  "tokenBreakdown": {
    "input": 789699,
    "output": 87484,
    "cacheRead": 21838592,
    "cacheWrite": 0,
    "reasoning": 0
  }
}
```

---

## 🔧 二、Token 压缩（RTK）

### 2.1 查看压缩收益

```bash
rtk gain
```

### 2.2 支持的自动压缩规则

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

### 2.3 Hermes 集成原理

- `rtk-hermes` 插件（v1.2.1）拦截所有 `terminal()` 工具调用
- 在执行前通过 `rtk rewrite <command>` 尝试重写
- **失败降级**：如果 RTK 不可用或无法重写，直接执行原命令（fail-open）
- 超时 2 秒，不会阻塞工作流

### 2.4 手动使用 RTK

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
rtk init --show
grep "rtk-rewrite" /root/.hermes/config.yaml
```

---

## 📋 三、快速用法速查

```bash
# === 用量统计 ===
tokscale graph --client hermes --today
tokscale graph --client hermes --week
tokscale graph --client hermes --since X --until Y
tokscale models --client hermes --light
tokscale monthly --client hermes --light

# === Token 压缩 ===
rtk gain

# === 路径 ===
TOKSCALE=/root/.hermes/node/bin/tokscale
RTK=/usr/local/bin/rtk
```

## ⚠️ 注意事项

- TokScale 安装在 `/root/.hermes/node/bin/tokscale`，不在全局 PATH 中
- 修改 `config.yaml` 后需重启 Hermes Gateway 才生效
- RTK 插件默认 2 秒超时，fail-open 降级
