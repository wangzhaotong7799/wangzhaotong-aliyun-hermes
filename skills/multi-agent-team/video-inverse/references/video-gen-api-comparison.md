# 🎬 AI视频生成平台 API 对比与接入指南

> 调研时间：2026-05-12
> 调研背景：影墨小队视频提示词逆向工程 → 下一步打通视频生成链路

---

## 一、主流平台对比总表

| 平台 | API Key | 排队 | 价格 | 性价比 | Python SDK | 中文支持 | 声音 | 分辨率 | 单次时长 |
|:----|:-------:|:----:|:----:|:------:|:----------:|:--------:|:----:|:-----:|:--------:|
| **通义万相** (Wan2.7) | ✅ 阿里云百炼已有 | 需激活 | ~¥0.5-1/次 | ⭐⭐⭐⭐⭐ | 直调REST | ✅ 最佳 | ❌ | 720p | 5-10s |
| **Kling** (可灵) | 申请开放 | 不排队 | ~¥1.5/秒 | ⭐⭐⭐⭐ | TechWithTy/kling | ✅ | ✅ | 1080p | 5-10s |
| **Seedance 2.0** | 需白名单 | ⚠️ 排队等 | ~$0.10/秒 | ⭐⭐⭐⭐ | seedance-api | ⚠️ 英文更佳 | ✅ | 2K | 4-15s |
| **Runway Gen-3** | 申请开放 | 不排队 | $0.15/秒 | ⭐⭐⭐ | 官方API | ❌ 英文 | ✅ | 1080p | 5-10s |
| **MiniMax** (海螺AI) | 申请开放 | 不排队 | ¥0.8/秒 | ⭐⭐⭐⭐ | REST API | ✅ | ❌ | 1080p | 6s |

---

## 二、通义万相 Wan2.7 详细调研

### 2.1 可用模型

通过 DashScope API 查询到的实际可用模型：

| 模型ID | 类型 | 状态 | 说明 |
|--------|:----:|:----:|------|
| `wan2.7-image` | 文生图 | ⚠️ 需async任务 | 基础图片生成 |
| `wan2.7-image-pro` | 文生图增强 | ⚠️ 需async任务 | 高质量图片生成 |
| `wan2.7-t2v` | 文生视频 ⭐*推荐* | ❌ url error | 文字→视频 |
| `wan2.7-i2v` | 图生视频 | ❌ url error | 图片→视频 |

### 2.2 API 测试记录

**成功验证的接口**：
- 视觉分析（图片理解）：✅ `compatible-mode/v1/chat/completions` — 通过 qwen3-vl-plus 模型可用
- 模型列表查询：✅ `compatible-mode/v1/models` — 返回 `wan2.7-image`, `wan2.7-image-pro`

**失败的接口**：
- 文生图：`AccessDenied` — "current user api does not support synchronous calls"
  - 需要 async task 模式：提交任务→poll直到完成
- 文生视频：`InvalidParameter` — "url error, please check url"
  - 可能原因：①API端点不对 ②模型未在该账号激活 ③需要单独开通视频生成服务
- 图生视频：同上

### 2.3 猜想：需要额外的开通步骤

通义万相的图像/视频生成能力可能需要：
1. 在阿里云百炼控制台**单独开通**视频生成服务
2. 或使用**不同的 API 端点**（非 OpenAI 兼容模式）
3. 或需要**单独申请**视频生成模型的访问权限

### 2.4 其他平台 SDK 速查

```bash
# Kling Python SDK
pip install kling-sdk  # 或使用 TechWithTy/kling (GitHub)
# 使用方式：
from kling import KlingClient
client = KlingClient(api_key="...")
result = client.text_to_video(prompt="...", model="kling-v2")

# Seedance API (非官方，需白名单)
# GitHub: https://github.com/seedance-api/seedance-api
# POST https://api.sedanceai.com/v2/generate
payload = {
    "prompt": "...",
    "model": "seedance-2.0-turbo",
    "aspect_ratio": "9:16",
    "api_key": "..."
}

# 多平台统一 SDK
# GitHub: https://github.com/vargHQ/sdk (⭐287)
# 一个API调Kling/Flux/Seedance/Sora/Wan
# 技术栈: JSX for videos, Vercel AI SDK
```

---

## 三、提示词平台适配要点

| 平台 | 最佳提示词语言 | 长度建议 | 特殊标记 |
|:----|:------------:|:--------:|:--------:|
| Kling | 中文 | 100-300字 | 自然语言分段 |
| Runway Gen-3 | 英文 | 50-150词 | `[SCENE START]...[SCENE END]` |
| Seedance 2.0 | 英文 | 100-300词/段 | `[00-05s]` 时间线 + `[SCENE START][SCENE END]` |
| MiniMax | 中文 | 100-300字 | 自然语言，故事化 |
| 通义万相 | 中文 | 50-200字 | 简洁描述 |

---

## 四、决策树：选哪个平台

```
需要生成的视频类型？
├── 珠宝/奢侈品/高画质 → Seedance 2.0 (2K)
├── 普通电商产品/走量
│   ├── 已有 Key → 通义万相（零成本启动）
│   └── 需申请 → Kling（最稳定国内）
├── 英文市场/海外客户 → Runway Gen-3
├── 故事感/剧情向 → MiniMax
└── 需要声音/配乐
    ├── 中文 → Kling
    └── 英文 → Runway / Seedance
```
