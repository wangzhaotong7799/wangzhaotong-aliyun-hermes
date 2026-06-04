# 🌐 多平台视频生成提示词优化指南

## 各平台核心参数对比

| 参数 | Kling（可灵） | Runway Gen-3 | Seedance 2.0 | MiniMax（海螺） | 通义万相 |
|:-----|:------------:|:------------:|:------------:|:--------------:|:--------:|
| 单次最大时长 | 5-10s | 5-10s | 4-15s | 6s | 5-10s |
| 分辨率 | 720p-1080p | 1080p | 720p-2K | 1080p | 720p |
| 帧率 | 24/30fps | 24fps | 24fps | 30fps | 24fps |
| 有声音 | ✅ 有 | ✅ 有 | ✅ 有 | ❌ 无 | ❌ 无 |
| 图生视频 | ✅ | ✅ | ✅ | ✅ | ✅ |
| 文本生视频 | ✅ | ✅ | ✅ | ✅ | ✅ |
| 中文提示词 | ✅ 最佳 | ⚠️ 支持一般 | ⚠️ 英文更佳 | ✅ 最佳 | ✅ 最佳 |
| API 可用 | ✅ 国内 | ✅ 国际 | ⚠️ 白名单 | ✅ 国内 | ✅ 国内 |

## 各平台提示词优化要点

### Kling（可灵）— 中文平台最简模式
**特点**：中文提示词效果最好，对自然语言理解强
**优化要点**：
- ✅ 直接使用中文自然语言描述
- ✅ 每个场景独立成段
- ✅ 简单直接的效果描述效果最好
- ❌ 不需要过多专业电影术语
- ⚠️ 建议控制在500字以内

**提示词模板**：
```
[场景名 + 时间]
[画面描述，包含主体、动作、光线]
[镜头运动，简单为主]
```

**最佳实践**：
```
开场（0-3秒）：暗调画面，一只手从阴影中伸出，一束冷光打在戒指上，碎钻瞬间闪耀。
转场（3-6秒）：手指在灯光下缓慢转动戒指，碎钻随转动不断折射出蓝白色光芒。
```

### Runway Gen-3 — 国际平台最稳定
**特点**：英文提示词为主，支持精细控制
**优化要点**：
- ✅ 必须用英文
- ✅ 支持 camera_shot 参数
- ✅ 详细的光线描述效果显著
- ✅ 可以使用 Style Reference Image
- ❌ 中文提示词效果差

**提示词模板**：
```markdown
[Scene Description]
[Actor/Action/Environment] with [Lighting Detail].
[Camera Movement], [Depth of Field].
[Mood/Atmosphere] atmosphere.

Style: [comma, separated, tags]
```

**最佳实践**：
```
A woman's elegant hand slowly emerging from deep shadow. A single cold spotlight hits a diamond pave ring at 45° — diamonds explode with brilliant refracted light. Slow motion, light traces across multi-faceted diamond surface. Dark background 80% black.

Style: Cinematic jewelry commercial, cold tone, high contrast, macro detail
```

### Seedance 2.0 — 电影级画质
**特点**：支持精确时间线，2K分辨率，角色一致性强
**优化要点**：
- ✅ 必须有 `[SCENE START]` / `[SCENE END]` 标记
- ✅ 使用 [00-05s] 时间线格式
- ✅ 详细描述每个镜头的起承转合
- ✅ 支持 Style Reference Image
- ✅ 声音设计也有效
- ⚠️ 英文效果优于中文

**提示词模板**：
```
[SCENE START]
[Duration marker] Shot N: [Title]
Detailed description with camera, lighting, action.
[SCENE END]

Style: [comma separated]
Camera: [shot type]
Lighting: [lighting description]
Mood: [emotion tags]
Color: [color palette]
```

**最佳实践**：
```
[SCENE START]
[00-03s] Shot 1: The Reveal. Dark ambient room, extreme close-up macro shot of elegant hand slowly emerging from shadow into cold spotlight. Each diamond facet catches light in sequence.
[SCENE END]

Style: Cinematic jewelry commercial, cold luxury aesthetic, editorial fashion
Camera: Macro extreme close-up, slow push in, shallow DOF f/1.4
Lighting: Single cold directional spotlight 45° upper left, high contrast chiaroscuro
Mood: Mysterious, elegant, captivating
Color: Cool white (#E8E8F0), silver (#C0C0D0), deep black background
```

### MiniMax（海螺AI）— 性价比之选
**特点**：画质好，故事感强，中文支持优秀
**优化要点**：
- ✅ 中文描述效果好
- ✅ 强调故事性和情感
- ✅ 可以写较长的连续描述
- ❌ 不支持声音输出
- ❌ 单次6秒，需拼接

### 通义万相（阿里云百炼）— 现有API最优选
**特点**：已有API Key，零成本启动
**优化要点**：
- ✅ 中文描述最佳
- ✅ 调用成本最低
- ✅ 国内网络无忧
- ❌ 单次5-10秒
- ❌ 画质720p
- ❌ 不支持声音

## 提示词长度优化参考

| 平台 | 最佳长度 | 最多限制 |
|------|:-------:|:--------:|
| Kling | 100-300字 | 500字 |
| Runway Gen-3 | 50-150词 | 400词 |
| Seedance 2.0 | 100-300词/段 | 分段不限 |
| MiniMax | 100-300字 | 500字 |
| 通义万相 | 50-200字 | 300字 |

## 提示词平台适配决策树

```
用户输入视频/需求
         ↓
需要配乐/声音？──────是────→ Kling / Runway / Seedance
         │否                    (通义万相/MiniMax无声音)
         ↓
画质优先？───────────是────→ Seedance 2.0 (2K)
         │否             或→ Runway Gen-3 (1080p)
         ↓
成本优先？───────────是────→ 通义万相 (已有API Key)
         │否
         ↓
国内可用优先？───────是────→ Kling / 通义万相
         │否
         ↓
                      MiniMax / Seedance 2.0
```
