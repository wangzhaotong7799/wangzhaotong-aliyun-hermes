---
name: token-manager
description: "Token管家 — 每日 Token 用量统计（TokScale）+ Token 压缩（RTK）一体化管理"
version: 1.3.0
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
| **TokScale** | `/root/.hermes/node/bin/tokscale` v3.0.0 | ✅ 可用 |
| **RTK** | `/usr/local/bin/rtk` v0.38.0 | ✅ 可用 |
| **rtk-hermes 插件** | Hermes `config.yaml` 已注册 `rtk-rewrite` | ✅ 已配置 |
| **RTK 全局 Hook** | `rtk hook claude` + `settings.json` | ✅ 已安装 |
| **累计节约** | 10.0M tokens (96.3%) / 1,148 commands | ✅ 运行中 |

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

### 1.5 🔁 降级方案：TokScale 不可用时（直接查询 Hermes DB）

TokScale 依赖 GitHub 网络（拉取 LiteLLM 定价文件），网络不稳定时会超时。此时可直接查询 Hermes 本地 SQLite 数据库获取用量数据。

**查询昨日用量（通用版本，无需改日期）：**

```bash
sqlite3 /root/.hermes/state.db "SELECT date(started_at, 'unixepoch') as day,
  COUNT(*) as session_count,
  COALESCE(SUM(message_count), 0) as total_messages,
  COALESCE(SUM(input_tokens), 0) as total_input,
  COALESCE(SUM(output_tokens), 0) as total_output,
  COALESCE(SUM(cache_read_tokens), 0) as total_cache_read,
  COALESCE(SUM(cache_write_tokens), 0) as total_cache_write,
  COALESCE(SUM(reasoning_tokens), 0) as total_reasoning,
  COALESCE(SUM(estimated_cost_usd), 0) as total_cost
FROM sessions
WHERE date(started_at, 'unixepoch') = date('now', '-1 day');
"
```

**按模型拆分昨日用量（通用版本，无需改日期）：**

```bash
sqlite3 /root/.hermes/state.db "
SELECT model, COUNT(*) as sessions, COALESCE(SUM(message_count), 0) as msgs,
  COALESCE(SUM(input_tokens), 0) as input,
  COALESCE(SUM(output_tokens), 0) as output,
  COALESCE(SUM(cache_read_tokens), 0) as cache_read,
  COALESCE(SUM(estimated_cost_usd), 0) as cost
FROM sessions WHERE date(started_at, 'unixepoch') = date('now', '-1 day')
GROUP BY model ORDER BY cost DESC;
"
```

**查询本月累计（逐日明细）：**

```bash
sqlite3 /root/.hermes/state.db "
SELECT date(started_at, 'unixepoch') as day,
  COUNT(*) as sessions, SUM(message_count) as msgs,
  SUM(input_tokens) as input, SUM(output_tokens) as output,
  SUM(cache_read_tokens) as cache_read
FROM sessions GROUP BY day ORDER BY day DESC LIMIT 31;
"
```

**Sessions 表关键字段：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `started_at` | REAL | Unix 时间戳，用 `date(started_at, 'unixepoch')` 转为日期 |
| `model` | TEXT | 模型名称（如 `deepseek-v4-flash`） |
| `message_count` | INTEGER | 消息条数 |
| `input_tokens` | INTEGER | 输入 Token |
| `output_tokens` | INTEGER | 输出 Token |
| `cache_read_tokens` | INTEGER | 缓存命中（免费） |
| `cache_write_tokens` | INTEGER | 缓存写入 |
| `reasoning_tokens` | INTEGER | 推理 Token |
| `estimated_cost_usd` | REAL | 估算费用（可能为 0，取决于模型配置） |
| `cost_status` | TEXT | `'unknown'` 表示未配置成本追踪 |

> ⚠️ **注意**：部分模型（如 `deepseek-v4-flash`）可能未配置成本追踪，`estimated_cost_usd` 和 `actual_cost_usd` 为 0。TokScale 有自己的定价逻辑，两者数据可能不一致。

### 1.6 手动费用估算（TokScale 不可用 + DB 费用为 0 时）

当 TokScale 超时且 Hermes DB 的 `estimated_cost_usd = 0` 时，可查询模型名称后使用已知定价手动估算费用。

**查询模型和用量：**
```bash
sqlite3 /root/.hermes/state.db "SELECT model, COUNT(*) as cnt, SUM(input_tokens) as input, SUM(output_tokens) as output, SUM(cache_read_tokens) as cache_read FROM sessions WHERE date(started_at, 'unixepoch') = date('now', '-1 day') GROUP BY model;"
```

**估算规则（以 deepseek-v4-flash 为例）：**

| 项目 | 价格（per 1M tokens） |
|------|:-------------------:|
| 输入（缓存命中） | **$0.0028** |
| 输入（缓存未命中） | **$0.14** |
| 输出 | **$0.28** |

- **缓存命中率的判断**：当 `cache_read_tokens > input_tokens` 时，可合理假设全部输入均为缓存命中价，因为缓存上下文大于当前输入。这是 cron 任务和重复会话中的常见情况。
- **保守估计**：若想给出中位估算，按 50% 缓存命中率计算（`input * 0.5` 按命中价 + `input * 0.5` 按未命中价 + output 按输出价）。
- **费用单位**：DeepSeek 官方定价为 USD，直接以 USD 展示。不乘以任何修正系数或汇率。
- **报告注明**：末尾加注「TokScale 估算，实际以 DeepSeek 官网账单为准」。

**按月累计估算示例：**
```bash
# 本月 1 号至昨天的累计
sqlite3 /root/.hermes/state.db "SELECT SUM(input_tokens), SUM(output_tokens), SUM(cache_read_tokens) FROM sessions WHERE strftime('%Y-%m', started_at, 'unixepoch') = strftime('%Y-%m', 'now', '-1 day') AND date(started_at, 'unixepoch') <= date('now', '-1 day');"
```

---

## 🔧 二、Token 压缩（RTK）

### 2.1 查看压缩收益

```bash
rtk gain                # 累计统计
rtk gain --daily        # 逐日明细（日报用这个）
rtk gain --weekly       # 按周汇总
rtk gain --monthly      # 按月汇总
```

输出示例：
```
Total commands:    206
Input tokens:      224.3K
Output tokens:     43.0K
Tokens saved:      181.4K (80.9%)
Efficiency meter: ███████████████████░░░░░ 80.9%
```

`rtk gain --daily` 输出示例（适合嵌入日报）：
```
Date            Cmds      Input     Output      Saved   Save%     Time
──────────────────────────────────────────────────────────────────────────
2026-05-12       206       5.8M      47.2K       5.7M   99.2%    128ms
──────────────────────────────────────────────────────────────────────────
TOTAL            519       6.0M     102.6K       5.9M   98.3%    242ms
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

## 💰 三、省钱操作指南

### 核心原则：数据源不强行统一

**TokScale 和提供商官网（如 DeepSeek 账单）对不上是常态。** 根因是 API `usage` 字段与账单计费口径不同，不是 TokScale 算错了。 
- ❌ 不拉公式"预测"官网账单（用户明确反对这一点）
- ✅ TokScale → 看趋势（今天比昨天多了少了）
- ✅ 提供商官网 → 看实付（精确金额）
- 报告末尾加注：`（TokScale 估算，实际以官网账单为准）`

### 3.1 核心矛盾：缓存未命中最烧钱

以 deepseek-v4-flash 为例，缓存未命中单价是命中的 **50 倍**（$0.14/M vs $0.0028/M）。因此费用大头不在总量，在**缓存未命中率**。

| 项目 | 占比（Token） | 占比（费用） | 原因 |
|-----|:-----------:|:----------:|------|
| 缓存命中 | ~97% | ~20% | $0.0028/M 白菜价 |
| 缓存未命中 | ~2% | **~69%** | $0.14/M 贵 50 倍 |
| 输出 | ~1% | ~11% | $0.28/M 中等 |

### 3.2 ✅ 省钱做法

| 操作 | 省什么 | 省多少 |
|-----|------|:-----:|
| **同一会话持续聊** | 避免重复加载系统提示词 | 每次节省 ~7K tokens 未命中 |
| **用 `/resume` 恢复旧会话** | 比开新会话省 70%+ | 缓存延续 |
| **发链接代替粘贴长文** | 避免原文留在历史中反复传输 | 省 90%+ |
| **发附件代替复制文件内容** | 我读一次后只留摘要 | 省 90%+ |
| **正常分段聊天** | 你的自然风格已是最佳 | — |
| **跨天前先 /resume 接续** | 避免隔夜缓存被清后的首条消息 | 省一次完整上下文加载 |

### 3.3 ❌ 烧钱行为

| 操作 | 为什么贵 |
|-----|---------|
| **频繁开新会话** | 每次系统提示词重新加载 → 缓存未命中 |
| **直接粘贴超长文字（>1000字）** | 原文留在对话历史中每轮都传 |
| **一次发大量零散消息** | 每条消息都可能触发新的 API 调用 |
| **跨夜后开新会话** | 缓存被 DeepSeek 清理 → 全量未命中 |

> **要点**：不是少说话，而是减少「缓存重新加载」。同一个话题持续聊，比开 5 个短会话省 5 倍。

### 3.4 模型能力限制

| 模型 | 支持看图 | 图片替代方案 |
|------|:-------:|------------|
| **deepseek-v4-flash**（当前） | ❌ | 截图 → 描述文字 |
| **deepseek-chat** | ❌ | 截图 → 描述文字 |
| **qwen3-vl-plus**（百炼） | ✅ | 直接发图片 URL |
| **qwen2.5-vl-7b**（百炼） | ✅ 轻量 | 简单图文识别 |

如需看图处理，需要通过百炼 API 单独调用视觉模型，DeepSeek 系列全线不支持多模态输入。

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

## 🧮 六、计费偏差核对（提供商门户 vs TokScale）

TokScale 的 Token 统计与提供商官网账单之间存在偏差是常见现象。**TokScale 的单价算法是正确的**（已验证与 DeepSeek 官方定价完全吻合），偏差来源于 **Token 数量口径不同**。

### 🚨 用户已明确纠正（2026-05-13）：不要拉公式

不要试图用任何公式（如 ×1.36、×汇率7.14等）来"预测"或"校正"提供商账单。用户对此的评价是——**"这都是估算"**。

**正确做法：**
- TokScale → 出多少写多少，**不要乘任何修正系数**
- 报告末尾统一加注：`（TokScale 估算，实际以 DeepSeek 官网账单为准）`
- 费用优先以 **CNY（人民币）** 展示，价格数字来自 TokScale 的 USD 输出原样呈现，不经过汇率/系数换算
- 用户看实付自己去看官网账单，我们不替他推算

### 6.1 已知偏差：DeepSeek 账单门户

| 项目 | DeepSeek 官网 | TokScale | 差额 | 倍率 |
|------|:-----------:|:--------:|:----:|:----:|
| 缓存命中 | 92,246,528 | 71,295,872 | +20,950,656 | 1.3x |
| 缓存未命中 | 6,437,886 | 1,268,507 | +5,169,379 | 5.1x |
| 输出 | 505,008 | 334,913 | +170,095 | 1.5x |
| **合计** | **99,189,422** | **72,899,292** | **+26,290,130** | **1.36x** |
| **实际费用** | **$1.3010** | **$0.4710** | **+$0.83** | **2.8x** |

**结论：DeepSeek 官网比 TokScale 多算约 36% 的 Token。** 根因可能是 API 返回的 `usage` 字段与账单计费口径不同，或聊天模板附加 Token、Tokenizer 差异。**不要尝试校正或拟合差距**——TokScale 和提供商门户各用各的，分别展示即可。

> 💡 **实践建议**：TokScale → 看趋势（今天比昨天多了还是少了）；提供商官网 → 看实付（精确金额）。两者并存不强行统一。详见 `references/billing-reconciliation.md`。

### 6.2 TokScale 定价缓存维护

**问题：** TokScale 从 GitHub Raw 拉取 LiteLLM 定价文件，网络不可达时会超时。
**解决：** 手动下载最新定价文件并更新本地缓存：

```bash
curl -sS --connect-timeout 10 --max-time 30 \
  "https://raw.githubusercontent.com/BerriAI/litellm/main/model_prices_and_context_window.json" \
  -o /tmp/litellm_pricing_latest.json

python3 -c "
import json, time, os
with open('/tmp/litellm_pricing_latest.json') as f:
    pricing = json.load(f)
cache_path = os.path.expanduser('~/.config/tokscale/cache/pricing-litellm.json')
if os.path.exists(cache_path): os.rename(cache_path, cache_path + '.bak')
with open(cache_path, 'w') as f: json.dump({'timestamp': int(time.time()), 'data': pricing}, f)
print(f'缓存已更新: {len(pricing)} 个模型')
"
```

**deepseek-v4-flash 不在 LiteLLM 官方定价库中**，TokScale 加载缓存后仍无法计算准确费用。需手动添加到缓存：

```bash
python3 << 'PYEOF'
import json, os, time
cache_path = os.path.expanduser('~/.config/tokscale/cache/pricing-litellm.json')
with open(cache_path) as f:
    cache = json.load(f)
data = cache.get('data', {})
# deepseek-v4-flash 定价（DeepSeek 官方：缓存命中 $0.0028/M, 未命中 $0.14/M, 输出 $0.28/M）
data['deepseek-v4-flash'] = {
    "max_tokens": 65536, "max_input_tokens": 131072, "max_output_tokens": 65536,
    "input_cost_per_token": 1.4e-07,          # $0.14/M（缓存未命中）
    "input_cost_per_token_cache_hit": 2.8e-09, # $0.0028/M（缓存命中）
    "output_cost_per_token": 2.8e-07,          # $0.28/M
    "cache_read_input_token_cost": 2.8e-09,
    "litellm_provider": "deepseek", "mode": "chat",
    "supports_function_calling": True, "source": "manual_add"
}
# 同时添加别名方便 TokScale 识别
for alias in ['openrouter/deepseek/deepseek-v4-flash', 'deepseek/deepseek-v4-flash']:
    data[alias] = data['deepseek-v4-flash'].copy()
cache['data'] = data; cache['timestamp'] = int(time.time())
with open(cache_path, 'w') as f: json.dump(cache, f)
print(f'deepseek-v4-flash 已添加到缓存，模型总数: {len(data)}')
PYEOF
```

验证生效：
```bash
# 检查不再有 LiteLLM JSON parse failed 警告
/root/.hermes/node/bin/tokscale graph --client hermes --today 2>/tmp/tokscale_stderr.txt
cat /tmp/tokscale_stderr.txt  # 应为空
```

### 6.3 deepseek-v4-flash 官方定价（截至 2026-06-09，经官方页面再确认）

| 项目 | 价格（per 1M tokens） |
|------|:-------------------:|
| 输入（缓存命中） | **$0.0028** |
| 输入（缓存未命中） | **$0.14** |
| 输出 | **$0.28** |

> 该模型不在 LiteLLM 官方定价数据库中。TokScale 查询不到时会使用未知回退策略。

---

## ⚠️ 注意事项

- **TokScale 路径**：安装在 `/root/.hermes/node/bin/tokscale`，不在全局 PATH 中
- **TokScale 网络依赖**：TokScale 启动时会尝试从 raw.githubusercontent.com 拉取 LiteLLM 定价文件。如果该地址无法访问（常见于国内服务器或网络抖动），TokScale 会重试 3 次后超时（每次约 20 秒），整个命令会 hang 住。→ **降级方案见 1.5 节；缓存更新见 6.2 节**
- **rtk-hermes 插件**：修改 `config.yaml` 后需重启 Hermes Gateway 才生效
- **RTK 超时**：插件默认 2 秒超时，不会阻塞正常命令执行
- **缓存命中率高**：DeepSeek 等提供商缓存命中率约 96-98%，实际净 Token 消耗远低于总量
- **费用数据缺失**：部分模型（如 `deepseek-v4-flash`）在 Hermes DB 中 `cost_status = 'unknown'`，`estimated_cost_usd` 为 0。TokScale 有自己的定价逻辑，两者费用数据可能不一致。参考 6.3 节手动定价。
- **rtk gain 数据是累计的**：使用 `rtk gain` 不带参数获得的是全量累计统计。日报应使用 `rtk gain --daily` 获取逐日明细。
- **RTK 数据可能不覆盖昨天**：`rtk gain --daily` 仅显示确实有 RTK 压缩活动的日期。如果某日没有命令行被 RTK 压缩（例如 Hermes 的 `rtk rewrite` 插件未触发），该日就不会出现在 `--daily` 输出中。此时日报应报告累计统计（`rtk gain` 的 TOTAL 行）并注明「昨日无 RTK 数据」。
- **提供商账单偏差**：TokScale/Hermes DB 的 Token 统计与提供商官网账单的偏差是常态（DeepSeek 约 +36%）。每日报告应注明数据来源和可信度。详见 `references/billing-reconciliation.md`。

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

**Cron 任务 Prompt 模板（自包含模式 — 推荐）：**

⚠️ **坑点：不要加载 SKILL.md 作为 cron skill** — SKILL.md 文件很大（本技能约 30K+ 字符），加载到 cron 上下文中会导致 agent 上下文溢出，agent 无法产出任何输出（session 表现为仅 user 消息无 assistant 响应）。**如果 cron job 的 `skills` 参数引用了本技能，务必移除并改用以下自包含 prompt：**

```yaml
# 正确配置：不加载技能，用自包含 prompt
# cronjob(action='create', prompt='...全文如下...', skills=[])
```

```
任务：生成昨日 Token 使用和节约情况报告

请按以下步骤执行并输出报告到终端（会自动投递到飞书）：

1. 计算昨天的日期（YYYY-MM-DD格式）

2. 查询昨日 TokScale 用量明细：
   /root/.hermes/node/bin/tokscale graph --client hermes --since {昨天日期} --until {昨天日期} 2>/dev/null
   → 如果 TokScale 返回错误或超时（30s 以上），降级到 Hermes DB：
     sqlite3 /root/.hermes/state.db "SELECT COUNT(*) as sessions, SUM(message_count) as msgs, SUM(input_tokens) as input, SUM(output_tokens) as output, SUM(cache_read_tokens) as cache_read, SUM(cache_write_tokens) as cache_write, SUM(estimated_cost_usd) as cost FROM sessions WHERE date(started_at, 'unixepoch') = '{昨天日期}';"

3. 查询 RTK 压缩节约统计（注意用 --daily）：
   rtk gain --daily 2>/dev/null | tail -5
   → 如果昨天没数据（RTK 仅记录有压缩活动的日期），用 rtk gain 2>/dev/null 取 TOTAL 行作为累计参考

4. 查询本月累计（本月1号到昨天）：
   sqlite3 /root/.hermes/state.db "SELECT SUM(input_tokens), SUM(output_tokens), SUM(cache_read_tokens) FROM sessions WHERE strftime('%Y-%m', started_at, 'unixepoch') = '本月' AND date(started_at, 'unixepoch') <= '{昨天日期}';"

5. 如果 TokScale 和 DB 都无 cost 数据（estimated_cost_usd = 0），根据模型名称手动估算：
   - 从 DB 查 model 名
   - deepseek-v4-flash 定价：缓存命中 $0.0028/M, 未命中 $0.14/M, 输出 $0.28/M
   - 当 cache_read > input 时，全部输入按缓存命中价计算（保守最低）
   - 不乘任何修正系数

6. 组装报告，格式如下：
   📊 Token 日报 · {昨天日期}
   ━━━━ 用量统计 ━━━━
   • 会话数：XX 次
   • 消息数：XX 条
   • Token 总量：XX (输入 XX + 输出 XX + 缓存 XX)
   • 费用：¥X.XX（TokScale 估算，实际以 DeepSeek 官网账单为准）

   ━━━━ 压缩节约 ━━━━
   • 累计压缩率：XX%（已省 XX tokens）
   • 昨日命令数：XX 条（若 RTK 无昨日数据，报告累计统计并注明）

   ━━━━ 本月累计 ━━━━
   • Token 总量：XX
   • 费用：¥X.XX

7. 重要注意事项：
   - 费用优先以 USD 展示（DeepSeek 定价为 USD），不乘汇率转 CNY
   - 报告末尾加注「TokScale 估算，实际以 DeepSeek 官网账单为准」
   - 不要乘任何修正系数（×1.36、×汇率等）
   - 如果 TokScale / DB / RTK 都返回错误，如实报告不编造
   - TokScale 超时时明确说明「TokScale 超时未响应，降级使用 Hermes DB」
```

**旧版模板（仍然可用但不再推荐 — 依赖 skill 加载）：**

```yaml

### 4.2 报告示例输出

```
📊 Token 日报 · 2026-05-07

━━━━ 用量统计 ━━━━
• 消息数：80 条
• Token 总量：22.7M (输入 789K + 输出 87K + 缓存 21.8M)
• 费用：¥1.43（TokScale 估算，实际以官网账单为准）

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
