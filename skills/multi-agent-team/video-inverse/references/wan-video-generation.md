# 🎥 通义万相 Wan2.7 图生视频 API 集成指南

> **模型**: `wan2.7-i2v-2026-04-25` | **单价**: ¥0.6/秒 (720P)
> **端点**: `POST https://dashscope.aliyuncs.com/api/v1/services/aigc/video-generation/video-synthesis`

## API 调用流程（异步任务）

### 步骤1：提交任务

```
POST https://dashscope.aliyuncs.com/api/v1/services/aigc/video-generation/video-synthesis
Headers:
  Authorization: Bearer ${ALIYUN_BAILIAN_API_KEY}
  X-DashScope-Async: enable        # 必选！缺失报"does not support synchronous calls"
  Content-Type: application/json

Body:
{
  "model": "wan2.7-i2v-2026-04-25",
  "input": {
    "prompt": "中文或英文提示词，描述视频内容",
    "media": [
      { "type": "first_frame", "url": "data:image/jpeg;base64,{base64_encoded_image}" }
    ]
  },
  "parameters": {
    "resolution": "720P",           # 720P 或 1080P
    "duration": 5,                  # 2-15 秒
    "prompt_extend": false,         # 是否智能改写
    "watermark": false              # 是否加水印
  }
}
```

### 步骤2：轮询任务状态

```
GET https://dashscope.aliyuncs.com/api/v1/tasks/{task_id}
Headers:
  Authorization: Bearer ${ALIYUN_BAILIAN_API_KEY}
```

轮询间隔约 15 秒，状态流转：PENDING → RUNNING → SUCCEEDED/FAILED

### 步骤3：下载结果

`SUCCEEDED` 后响应中包含 `video_url`，有效期 24 小时。

## 关键参数

| 参数 | 必选 | 说明 |
|------|:----:|------|
| `media.type` | ✅ | `first_frame`(首帧) / `last_frame`(尾帧) / `driving_audio`(驱动音频) / `first_clip`(视频续写) |
| `resolution` | ❌ | 720P (默认) / 1080P |
| `duration` | ❌ | 2-15秒，默认5秒 |
| `prompt_extend` | ❌ | true/false，短prompt建议开启 |
| `watermark` | ❌ | true/false |

## 提示词写作要点

- **中英文均可**，但中文对场景理解更好
- 包含：光线描述 + 运镜 + 动作 + 色调 + 情绪
- 图生视频时注意：**首帧决定了构图基线**，prompt 描述的动作不要与首帧构图矛盾
- 长度建议：100-500 字，越精确效果越好

## 三生任务模式

| 模式 | media 组合 | 说明 |
|------|-----------|------|
| 首帧生视频 | `first_frame` | 基于首帧图像生成后续画面 |
| 首帧+音频 | `first_frame` + `driving_audio` | 图像+音频驱动 |
| 首尾帧生视频 | `first_frame` + `last_frame` | 首帧→尾帧过渡 |
| 视频续写 | `first_clip` | 基于现有视频片段续写 |

## 🎬 Wan2.7 Creative Video Transfer（视频→视频风格迁移）

### 这是什么？

这是 Wan2.7 **最适合「换产品翻拍」** 的模式！官方描述：

> **Creative Video Transfer**: "One-click replication of dynamics, from complex character motions to cinematic camera work."
>
> **Instructional Video Editing**: "Recreate visuals, plots, and scenes with precise text prompts and multi-image guidance."

简单说：给 Wan2.7 一个参考视频，告诉它「保持这个运镜、这个动作、这个光线——但是把产品换成我们的」，它就能直接生成。

### 与 i2v 模式对比

| 维度 | i2v（当前在用） | Creative Video Transfer（推荐） |
|------|----------------|-------------------------------|
| 输入 | 单张首帧图片 | 参考视频 + 产品图 + 文本指令 |
| 输出 | 从首帧延展 | 保留参考视频的运镜/动态/节奏 |
| 产品替换 | 需手动描述产品外观 | 参考视频中的产品自动被替换 |
| 运镜保持 | 弱（首帧只能定构图基线） | **强（直接复制运镜轨迹）** |
| 最佳场景 | 无参考视频的纯生成 | **有爆款视频作为参考模板** |

### 调用方式（推测，基于官方文档）

```
POST https://dashscope.aliyuncs.com/api/v1/services/aigc/video-generation/video-synthesis
Headers:
  Authorization: Bearer ${ALIYUN_BAILIAN_API_KEY}
  X-DashScope-Async: enable
  Content-Type: application/json

Body:
{
  "model": "wan2.7-i2v-2026-04-25",
  "input": {
    "prompt": "把视频中的产品替换为[我们的产品]，保持相同的运镜、光线和构图。新产品的特征是[颜色/材质/形状描述]",
    "media": [
      { "type": "first_clip", "url": "data:video/mp4;base64,{参考视频}" },
      { "type": "first_frame", "url": "data:image/jpeg;base64,{新产品图}" }
    ]
  },
  "parameters": {
    "resolution": "720P",
    "duration": 5,
    "prompt_extend": false,
    "watermark": false
  }
}
```

**注意**：Creative Video Transfer 的具体参数格式需查阅阿里云官方文档确认。如果 `first_clip` 不生效，可以尝试用 `first_frame`（首帧）作为参考图，然后在 prompt 中描述：「保持这个构图和光线，但把画面中的 X 产品替换为 Y 产品」。

### Creative Video Transfer vs 我们的 Prompt 逆向工程

```
          传统方式（当前）                  Creative Video Transfer（目标）
爆款视频 ──→ 帧级分析 ──→ 写prompt ──→ 生成    爆款视频 ──→ 直接作为输入端
                                                         ↑
我们的产品图 ──────────────────────────→                产品图作为参考
                                                         ↑
                                                prompt只需描述「怎么替换」
```

## 费用计算

| 分辨率 | 单价 | 5s | 10s | 15s | 30s | 70s |
|:-----:|:----:|:--:|:---:|:---:|:---:|:---:|
| 720P | ¥0.6/秒 | ¥3 | ¥6 | ¥9 | ¥18 | ¥42 |
| 1080P | ~¥0.73/秒 | ~¥3.7 | ~¥7.3 | ~¥11 | ~¥22 | ~¥51 |

## 避坑

1. **URL 连字符**：端点是 `video-synthesis`（连字符），不是 `video_synthesis`（下划线）
2. **Async 头**：必须传 `X-DashScope-Async: enable`，否则报 synchronous calls 错误
3. **Base64 传图**：格式 `data:image/jpeg;base64,{data}`，文件 ≤20MB
4. **API Key**：用 `ALIYUN_BAILIAN_API_KEY`，`wan2.7-t2v`/`wan2.7-i2v` 等视频模型不兼容 OpenAI chat endpoint
5. **生成时间**：5秒视频约 1-3 分钟，10秒约 3-5 分钟，15秒约 5-8 分钟

## Python 调用脚本模板

参考 `/tmp/gen_segments.py`（或 `/root/wangzhaotong-hermes/videos/` 中的已生成版本）：

```python
import base64, json, os, time, urllib.request

API_KEY = os.environ["ALIYUN_BAILIAN_API_KEY"]

def submit_video_task(prompt, img_path, duration=10):
    with open(img_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")
    
    payload = {
        "model": "wan2.7-i2v-2026-04-25",
        "input": {
            "prompt": prompt,
            "media": [{"type": "first_frame", "url": f"data:image/jpeg;base64,{b64}"}]
        },
        "parameters": {"resolution": "720P", "duration": duration,
                       "prompt_extend": False, "watermark": False}
    }
    
    req = urllib.request.Request(
        "https://dashscope.aliyuncs.com/api/v1/services/aigc/video-generation/video-synthesis",
        data=json.dumps(payload).encode(),
        headers={"Authorization": f"Bearer {API_KEY}",
                 "X-DashScope-Async": "enable", "Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        result = json.loads(resp.read())
    task_id = result["output"]["task_id"]
    
    for _ in range(40):  # 最多10分钟
        time.sleep(15)
        poll = json.loads(urllib.request.urlopen(
            urllib.request.Request(
                f"https://dashscope.aliyuncs.com/api/v1/tasks/{task_id}",
                headers={"Authorization": f"Bearer {API_KEY}"})
        ).read())
        status = poll["output"]["task_status"]
        if status == "SUCCEEDED":
            return poll["output"]["video_url"]
        elif status in ("FAILED", "CANCELED"):
            raise Exception(f"Task failed: {poll}")
    raise Exception("Timeout")
```
