# 🖼️ Auxiliary Vision 配置指南

## 为什么需要单独配置？

Hermes Agent 的 `vision_analyze` 工具使用 `auxiliary.vision` 配置块调用视觉模型，**不使用当前会话的主模型**。这意味着：

1. 主模型是 DeepSeek/GPT-4 → **不支持图像** → `vision_analyze` 报错 `unknown variant "image_url"`
2. 即使主模型支持图像，auxiliary 的 `api_key` 需要单独设置，不会自动继承 provider 的 key

## 完整配置步骤

### 1. 确认视觉模型提供商

```bash
# 查看已有 providers
grep -E "name:|api_key:" ~/.hermes/config.yaml | grep -v "auxiliary" | head -10
```

常见支持视觉的提供商：
- 阿里云百炼 DashScope → `qwen-vl-max`, `qwen3-vl-plus`, `qwen3-vl-flash`
- OpenAI → `gpt-4o`, `gpt-4o-mini`
- Anthropic → `claude-3.5-sonnet` (需配置时区)
- Google → `gemini-2.0-flash`

### 2. 检查 API Key

```bash
# 确认 provider 的 API key 已存在
grep "KEY_NAME" ~/.hermes/.env

# 例：阿里云百炼
# provider api_key: ${ALIYUN_BAILIAN_API_KEY} 或 ${DASHSCOPE_API_KEY}
# 确认该变量名有值
```

### 3. 配置 auxiliary.vision

```bash
# 设置 provider 和 model
hermes config set auxiliary.vision.provider aliyun-bailian
hermes config set auxiliary.vision.model qwen3-vl-plus-2025-09-23

# ⚠️ 关键！设置 API Key（不继承 provider 配置）
# ${ENV_VAR} 语法在此处可能不生效，需放实际值
hermes config set auxiliary.vision.api_key "sk-xxx..."
```

### 4. 验证

```bash
# 查看最终配置
grep -A 5 "auxiliary:" ~/.hermes/config.yaml
```

期望输出类似：
```yaml
auxiliary:
  vision:
    provider: aliyun-bailian
    model: qwen3-vl-plus-2025-09-23
    api_key: sk-xxx...
```

### 5. 测试

尝试调用 `vision_analyze` 分析任意图片。如果仍返回 401：
- 确认 API key 在 `.env` 中和在 `auxiliary.vision.api_key` 中一致
- 确认该 API key 有调用该模型的权限（阿里云百炼需开通模型服务）
- 确认模型名在 provider 的 models 列表中

## ⚠️ 常见陷阱

### 陷阱 1：配视觉时误改默认模型

**情景**: 用户说"帮我配阿里云百炼"，你配了 `custom_providers` + `auxiliary.vision`，然后顺手把 `model.default` 切换到阿里云、`fallback_providers` 设成 deepseek。

**结果**: 用户纠正"主模型还是用 deepseek，需要视频时候再调阿里云百炼"。

**正确做法**: 配视觉模型时，只动 `auxiliary.*` 配置块。不要动 `model.default` / `model.provider` / `fallback_providers`，除非用户明确要求切换主模型。

```
改动范围:
  ✅ custom_providers → 新增阿里云百炼 provider 配置
  ✅ .env → 添加 ALIYUN_BAILIAN_API_KEY
  ✅ auxiliary.vision → 设 provider/model/api_key
  ❌ model.default → 不改
  ❌ fallback_providers → 不改
```

### 陷阱 2：api_key 不继承

`auxiliary.vision.api_key` **不继承** provider 的 key 配置。即使 provider 已配 `${ALIYUN_BAILIAN_API_KEY}`，auxiliary 下也需要显式写入实际值。

## 常见错误排查

| 错误 | 原因 | 修复 |
|------|------|------|
| `unknown variant "image_url"` | auxiliary.vision 回退到主模型 | 显式设置 provider + model |
| `401 Invalid API key` | API key 为空或不正确 | 手动设置 `auxiliary.vision.api_key` |
| `404 Model not found` | 模型名错误或未开通 | 检查 provider models 列表 |
| `413 Request too large` | 图片太大 | `vision_analyze` 会自动缩放 |

## 推荐模型选型

| 场景 | Provider | 模型 | 速度 | 质量 |
|------|----------|------|------|------|
| 快速批量分析 | aliyun-bailian | qwen3-vl-flash | ⚡快 | 中等 |
| 日常使用 | aliyun-bailian | qwen3-vl-plus | 🏃中 | 良好 |
| 精确分析 | aliyun-bailian | qwen-vl-max | 🐢慢 | 优秀 |
| 高质量 | openai | gpt-4o | 🐢慢 | 优秀 |
