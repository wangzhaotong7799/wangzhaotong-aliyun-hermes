# 阿里云百炼（DashScope）完整配置手册

> 从零到一：将阿里云百炼设为 Hermes Agent 的默认 LLM 提供商

## 适用场景

- 首次接入阿里云百炼
- 从其他提供商（如 DeepSeek、OpenAI）切换到阿里云百炼
- 同时配好视觉辅助 + 回退兜底

## 前置条件

- 阿里云百炼控制台已开通：https://bailian.console.aliyun.com
- 已创建 API Key（API-KEY 管理页面）
- Hermes Agent 已安装并正常运行

## 完整配置步骤（4 步）

### 第 1 步：写入 API Key 到 .env

```bash
echo "ALIYUN_BAILIAN_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx" >> ~/.hermes/.env
```

**注意：** key 写在 `.env` 中，不要直接写进 `config.yaml`。`custom_providers` 里用 `${ALIYUN_BAILIAN_API_KEY}` 语法引用。

### 第 2 步：配置 custom_providers

确认 `~/.hermes/config.yaml` 中有 `aliyun-bailian` provider：

```yaml
custom_providers:
- name: aliyun-bailian
  base_url: https://dashscope.aliyuncs.com/compatible-mode/v1
  api_key: ${ALIYUN_BAILIAN_API_KEY}
  api_mode: chat_completions
  models:
    # 文本模型
    qwen-plus-2025-12-01:
      type: "文本模型"
    deepseek-v3.2:
      type: "文本模型"
    # 视觉模型
    qwen3-vl-plus-2025-09-23:
      type: "视觉模型"
    # ... 其他模型
```

**模型分类：**
- `"文本模型"` — 纯文本对话
- `"视觉模型"` — 支持图片/视频帧输入

### 第 3 步：切换默认模型 + 配 auxiliary.vision + 设 fallback

```yaml
# 3a. 默认模型
model:
  default: qwen-plus-2025-12-01   # 主力模型
  provider: aliyun-bailian         # 默认提供商

# 3b. fallback 兜底（可选）
fallback_providers: [deepseek]     # 原提供商降级为回退

# 3c. auxiliary.vision（⚠️ 关键坑）
auxiliary:
  vision:
    provider: aliyun-bailian
    model: qwen3-vl-plus-2025-09-23
    api_key: sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx  # ⚠️ 必须写实际值！
    # ${ENV_VAR} 语法在 auxiliary.* 中不生效
```

**⚠️ 铁则：`auxiliary.vision.api_key` 不继承 provider 的 `${VAR}` 引用。** 即使 provider 里写了 `${ALIYUN_BAILIAN_API_KEY}`，auxiliary vision 的 api_key 仍然为空，必须显式写入实际密钥值，否则视觉分析会返回 401。

### 第 4 步：验证

```bash
# 4a. 确认 .env
grep ALIYUN_BAILIAN ~/.hermes/.env
# 输出: ALIYUN_BAILIAN_API_KEY=sk-xxx

# 4b. 确认 model 段
grep -A2 '^model:' ~/.hermes/config.yaml
# 输出:
# model:
#   default: qwen-plus-2025-12-01
#   provider: aliyun-bailian

# 4c. 确认 fallback
grep fallback_providers ~/.hermes/config.yaml
# 输出: fallback_providers: [deepseek]

# 4d. 确认 auxiliary.vision
grep -A5 'vision:' ~/.hermes/config.yaml
# 输出:
#   vision:
#     provider: aliyun-bailian
#     model: qwen3-vl-plus-2025-09-23
#     base_url: ''
#     api_key: sk-xxx...
```

## 推荐主力模型选型

| 模型 | 特点 | 推荐场景 |
|------|------|----------|
| **qwen-plus-2025-12-01** | 平衡质量/速度/价格 | 日常主力（推荐⭐） |
| **qwen3.5-plus-2026-02-15** | 最新一代 Plus | 追求最新能力 |
| **qwen-turbo-2025-07-28** | 极速、低成本 | 批量处理/轻量任务 |
| **deepseek-v3.2** | 阿里托管版 DS | 已有 DS 习惯的用户 |
| **qwen3-235b-a22b** | 最强能力 | 复杂推理/长文分析 |

## 视觉辅助模型选型

| 模型 | 速度 | 质量 | 场景 |
|------|------|------|------|
| qwen3-vl-flash-2025-10-15 | ⚡快 | 中等 | 批量快速帧分析 |
| qwen3-vl-plus-2025-09-23 | 🏃中 | 良好 | 日常使用（推荐⭐） |
| qwen3-vl-32b-instruct | 🐢慢 | 优秀 | 精确分析 |
| qwen-vl-max-2025-08-13 | 🐢慢 | 优秀 | 高精度理解 |
| qwen3-vl-235b-a22b-instruct | 🐢极慢 | 最强 | 深度分析 |

## 故障排查

| 现象 | 原因 | 修复 |
|------|------|------|
| `401 Invalid API key` | auxiliary.vision 的 api_key 为空 | 显式写入 actual key（非 ${VAR}） |
| `403 Forbidden - 无权` | API key 无模型权限 | 阿里云百炼控制台开通模型服务 |
| `404 Model not found` | 模型名不在 provider 列表中 | 检查 custom_providers 下的 models |
| 模型卡死/超时 | 免费额度用完 | 检查阿里云账户余额及配额 |

## 生效条件

- `model.default` + `model.provider` → 新会话生效（`/reset` 或重开 hermes）
- `auxiliary.vision` → 即时生效（已运行时重启 gateway）
- `.env` → 新进程生效
