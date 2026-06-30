# 计费偏差核对指南

## 问题：提供商账单 vs TokScale 对不上

TokScale 统计的 Token 消耗与提供商官费用管理门户（如 DeepSeek 官网账单）之间有显著偏差是常见现象。本文档记录核对方法和已知偏差。

---

## 一、核对方法

### 1.1 获取提供商账单数据

从提供商的费用管理门户或 API 获取原始用量数据，记下：
- 缓存命中 Token 数
- 缓存未命中 Token 数  
- 输出 Token 数
- 总 Token 数

### 1.2 获取 TokScale/Hermes DB 数据

```bash
# 方法一：TokScale 命令
tokscale graph --client hermes --since YYYY-MM-DD --until YYYY-MM-DD --json

# 方法二：直接查询 Hermes DB（TokScale 不可用时）
sqlite3 /root/.hermes/state.db "
SELECT
  date(started_at, 'unixepoch') as day,
  SUM(input_tokens) as cache_miss_input,
  SUM(cache_read_tokens) as cache_hit_input,
  SUM(output_tokens) as output,
  SUM(message_count) as messages,
  SUM(api_call_count) as api_calls
FROM sessions
WHERE date(started_at, 'unixepoch') = 'YYYY-MM-DD'
GROUP BY day;
"
```

### 1.3 对比表格模板

| 项目 | 提供商官网 | TokScale | 差额 | 倍率 |
|------|:---------:|:--------:|:----:|:----:|
| 缓存命中 | A | B | A-B | A/B |
| 缓存未命中 | C | D | C-D | C/D |
| 输出 | E | F | E-F | E/F |
| **合计** | **A+C+E** | **B+D+F** | **差** | **比** |

---

## 二、已知提供商偏差

### 2.1 DeepSeek 官方账单 vs TokScale

**数据来源：** 2026-05-13 实测对比（模型 deepseek-v4-flash）

| 项目 | DeepSeek 官网 | TokScale/Hermes DB | 差额 | 倍率 |
|------|:-----------:|:-----------------:|:----:|:----:|
| 缓存命中 | 92,246,528 | 71,295,872 | +20,950,656 | **1.3x** |
| 缓存未命中 | 6,437,886 | 1,268,507 | +5,169,379 | **5.1x** |
| 输出 | 505,008 | 334,913 | +170,095 | **1.5x** |
| **合计** | **99,189,422** | **72,899,292** | **+26,290,130** | **1.36x** |

**DeepSeek 实际费用（按 deepseek-v4-flash 官方价计算）：**
- 缓存命中：92,246,528 × $0.0028/M = **$0.2583**
- 缓存未命中：6,437,886 × $0.14/M = **$0.9013**
- 输出：505,008 × $0.28/M = **$0.1414**
- **总计：$1.3010**

**TokScale 费用：$0.4710**

**结论：DeepSeek 官网多算约 36% 的 Token，费用差距约 2.8 倍。**
TokScale 使用的定价算法与官方定价完全吻合，偏差来源于 Token 数量，而非单价。

### 2.2 偏差的根因

可能原因（按可能性排序）：

1. **DeepSeek API 返回的 usage 字段与账单计费口径不同** — Hermes 存储的是 API 响应中 `usage` 字段的值，而 DeepSeek 账单门户可能使用不同的计算方式
2. **特殊 Token / 格式 Token 附加** — 聊天模板额外添加的 `<|im_start|>`、`<|im_end|>` 等 token 可能不被 API `usage` 字段完整报告
3. **Tokenizer 差异** — 客户端使用的 tokenizer 与 DeepSeek 服务端实际计费的 tokenizer 可能有差异
4. **缓存粒度差异** — DeepSeek 对缓存的判断可能比 Hermes 更严格，导致部分在 Hermes 视为缓存的 token 在 DeepSeek 被计为未命中

> ⚠️ **实践原则**：TokScale → 看趋势（今天比昨天多了还是少了）；提供商官网 → 看实付（精确金额）。两者并存，**不要尝试拉公式"预测"官网账单**。偏差无法精确归因，强行校正只会制造虚假精度。

---

## 三、TokScale 定价缓存维护

### 3.1 问题现象

TokScale 启动时会尝试从 `raw.githubusercontent.com/BerriAI/litellm/main/model_prices_and_context_window.json` 拉取 LiteLLM 定价文件。如果该地址不可达（国内服务器常见），TokScale 会重试 3 次后超时，导致所有命令 hang 住。

### 3.2 手动更新缓存

```bash
# 1. 下载最新定价文件
curl -sS --connect-timeout 10 --max-time 30 \
  "https://raw.githubusercontent.com/BerriAI/litellm/main/model_prices_and_context_window.json" \
  -o /tmp/litellm_pricing_latest.json

# 2. 包装为 TokScale 缓存格式并替换
python3 -c "
import json, time, os

with open('/tmp/litellm_pricing_latest.json') as f:
    pricing = json.load(f)

cache_data = {
    'timestamp': int(time.time()),
    'data': pricing
}

# 备份旧缓存
cache_path = os.path.expanduser('~/.config/tokscale/cache/pricing-litellm.json')
if os.path.exists(cache_path):
    os.rename(cache_path, cache_path + '.bak')

with open(cache_path, 'w') as f:
    json.dump(cache_data, f)

print(f'缓存已更新: {len(pricing)} 个模型')
"
```

### 3.3 验证缓存是否生效

```bash
# 成功输出 JSON 表示 TokScale 可用
tokscale graph --client hermes --today --json | python3 -c "import json,sys; d=json.load(sys.stdin); print(f'可用 ✅ ({len(d.get(\"contributions\",[]))} 天数据)')"
```

---

## 四、deepseek-v4-flash 官方定价（截至 2026-06-09，经官方页面再确认）

| 项目 | 价格（per 1M tokens） |
|------|:-------------------:|
| 输入（缓存命中） | **$0.0028** |
| 输入（缓存未命中） | **$0.14** |
| 输出 | **$0.28** |

> 注意：deepseek-v4-flash 不在 LiteLLM 官方定价数据库（`model_prices_and_context_window.json`）中。TokScale 使用此模型名称查询时找不到条目，会使用 unknown fallback。但 DeepSeek 账单门户按上述定价计费。

### 手动估算方法

当 Hermes DB 的 `estimated_cost_usd = 0` 且 TokScale 不可用时：

1. **查模型名**：`SELECT model, SUM(input_tokens), SUM(output_tokens), SUM(cache_read_tokens) FROM sessions WHERE ... GROUP BY model`
2. **判断缓存命中率**：若 `cache_read_tokens > input_tokens`，所有输入视为缓存命中（最低估计）。想给中位值，按 50% 命中率计算。
3. **套用定价**：缓存命中 $0.0028/M, 未命中 $0.14/M, 输出 $0.28/M
4. **不乘修正系数**：展示原始美元数字，不加汇率转换。

### 自定义 Hermes 成本配置

如需在 Hermes DB 中记录准确费用，可在 Hermes 的模型配置中加入成本参数（待确认 Hermes 是否支持自定义 pricing）。

---

## 📉 六、降低 Token 费用的实践指南

### 核心原则

费用大头在**缓存未命中**（占总量 ~2% 却贡献 ~69% 的费用），因为 deepseek-v4-flash 缓存未命中单价（$0.14/M）是缓存命中（$0.0028/M）的 **50 倍**。

### 省钱操作

| 操作 | 效果 | 说明 |
|-----|:----:|------|
| **同一话题持续聊** | 省 70%+ 未命中 | 换话题不换会话，缓存延续 |
| **发链接代替粘贴长文** | 省 90%+ | 我 web_extract 读完只存摘要，原文不留在历史 |
| **发附件代替复制文件** | 省 90%+ | 脚本读一次，只留结果 |
| **/resume 恢复会话** | 省首条未命中 | 比开新会话缓存延续 |
| **跨日后 /resume 续旧会话** | 省一次完整加载 | 隔夜缓存被清后首条最贵 |
| **系统提示词大的会话别频繁新建** | 省 7K+/次 | 每会话的系统提示词 ~19-23K chars |

### 烧钱行为

| 操作 | 原因 |
|------|------|
| 频繁开新会话 | 每次重新加载系统提示词 → 未命中 |
| 直接粘贴超长文字（>1000字） | 原文留在历史每轮都传 |
| 跨夜后开新会话 | 缓存被清理 → 全量重新加载 |

### 进度续聊指南

当需要换话题或跨天继续时，优先尝试：
1. 同一个会话直接换话题（最省）
2. 用 Hermes 的 `/sessions` 或 `/resume` 恢复旧会话（中度省）
3. 万不得已才新开会话（最贵）

---

## 附：USD 报告规范

- 所有费用报告以 **美元（USD）** 展示（DeepSeek 官方定价页面仅发布 USD）
- 直接呈现原始数字，**不做汇率/系数换算**，不试图匹配提供商账单
- 格式：`$X.XX（DB 估算，实际以 DeepSeek 官网账单为准）`

---

## 五、快速诊断流程

当用户报「TokScale 和某某平台账单对不上」时：

1. **确认数据源一致** — 确认查的是同一天、同一个模型
2. **获取三方数据** — 提供商官网 vs TokScale vs Hermes DB SQL
3. **计算倍率** — 提供商总量 ÷ TokScale 总量，得到偏差系数
4. **定位瓶颈项** — 看缓存命中、缓存未命中、输出三者中哪个偏差最大
5. **排除定价因素** — 用提供商官方价手动算一遍，确认不是单价问题
6. **给出校准建议** — 偏差 <10% 忽略，>20% 建议标记并手动核对
