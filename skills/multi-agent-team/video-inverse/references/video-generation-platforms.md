# 🎬 视频生成平台对比与集成指南

## 调研结论（2026-05-12）

| 平台 | API状态 | 排队 | 价格 | 性价比 | Python SDK | 说明 |
|------|:-------:|:----:|:----:|:------:|:---------:|------|
| **阿里云百炼·通义万相** `wanx-v1-0521` | ✅ **已有Key** | 不排队 | ~¥0.5-1/次 | ⭐⭐⭐⭐⭐ | 已有阿里云Key | 已在config.yaml中，视觉模型类型 |
| **Kling（可灵）** | 开放申请 | 不排队 | ~¥1.5/秒(国内) | ⭐⭐⭐⭐ | `TechWithTy/kling` (⭐8) | 国内稳定首选 |
| **Seedance 2.0** | 需白名单 | ⚠️ 排队 | ~$0.10/秒 | ⭐⭐⭐⭐ | `seedance-api` (⭐26) | 画质2K，角色一致性强 |
| **Runway Gen-3** | 开放申请 | 不排队 | $0.15/秒 | ⭐⭐⭐ | 官方REST API | 成熟稳定，国际最广 |
| **MiniMax（海螺AI）** | 开放申请 | 不排队 | ¥0.8/秒 | ⭐⭐⭐⭐ | REST API | 画质好，故事感强 |

## 多平台统一SDK

`vargHQ/sdk` (⭐287) — 一个API调多个平台：
- Kling, Flux, ElevenLabs, Sora, Seedance, Wan
- 基于 Vercel AI SDK
- TypeScript 实现

## 通义万相检查与使用

### 配置文件位置
```yaml
# 在 ~/.hermes/config.yaml 中
custom_providers:
  - name: aliyun-bailian
    models:
      wanx-v1-0521:
        type: "视觉模型"  # 视频/图像生成模型
```

### 调用方式（Python）
```python
# 通义万相API调用示例
import requests, json, os

api_key = os.environ.get("ALIYUN_BAILIAN_API_KEY")
url = "https://dashscope.aliyuncs.com/compatible-mode/v1/images/generations"

payload = {
    "model": "wanx-v1-0521",
    "input": {
        "prompt": "描述性提示词",
        "size": "720x1280",
        "n": 1
    }
}

headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
}

# response = requests.post(url, json=payload, headers=headers)
```

### 注意事项
- 通义万相是图像生成模型，确认是否支持视频生成需要实际测试
- 阿里云百炼还提供了 `animate-anyone` 模型（视觉模型类型），可能支持视频
- 当前配置中 `wanx-v1-0521` 从未被实际调用过

## 平台选择决策树

```
需要声音/配乐？──是──→ Kling / Runway / Seedance
   │否
   ↓
画质优先？──────是──→ Seedance 2.0 (2K)
   │否
   ↓
成本优先？──────是──→ 通义万相 (已有Key零成本)
   │否
   ↓
国内可用？──────是──→ Kling / 通义万相
   │否
   ↓
        MiniMax / Runway
```
