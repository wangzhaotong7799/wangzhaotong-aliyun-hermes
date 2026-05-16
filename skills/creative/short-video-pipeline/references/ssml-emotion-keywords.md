# SSML 情感关键词映射表

> 用于 `build_ssml_with_emotion()` 函数的逐句情感判断。
> 在 `EMOTION_KEYWORDS` 字典中定义，匹配到关键词即赋予对应情感标签。
> 未匹配的句子默认 `calm`。

## 情感 → 关键词 → SSML标签

| 情感 | 关键词（匹配即触发） | styledegree |
|:---|:---|---:|
| **fearful** | 掐住脖子、掐死、掐痕、掐着脖子、尸体、鬼、镜子里的、镜中人、拖进、挣扎、掐着、影子、另一个、僵住了、颤抖、噩梦、没气、死、死去、死亡、害怕、恐怖、怪物、血、杀死、勒 | 1.5~2（含"掐住/掐死/尸体/拖进"=2，其余1.5） |
| **sad** | 无儿无女、病倒了、无人照顾、无能为力、孤坟、哭了、流泪、难过、悲伤、可怜 | 1.5 |
| **angry** | 生气、指着、恶狠狠、吼道、怒、恨、大骂 | 2 |
| **calm** | 很久以前、从前、有一天、以前、原来、一直 | 不加标签（纯文本输出） |

## 使用方式

```python
from generate_horror_video_v7 import build_ssml_with_emotion

ssml_text = build_ssml_with_emotion(story_text, "zh-CN-YunyangNeural")
# edge-tts auto-detects SSML when text starts with <speak>
communicate = edge_tts.Communicate(ssml_text, "zh-CN-YunyangNeural")
await communicate.save("output.mp3")
```

## 注意

- 句子匹配是简单的 `keyword in sentence` 判断，不区分上下文
- 同一句子匹配多个情感时，按 `fearful > angry > sad > calm` 优先级取第一个
- 如有需要可扩展关键词列表，无需修改函数逻辑
