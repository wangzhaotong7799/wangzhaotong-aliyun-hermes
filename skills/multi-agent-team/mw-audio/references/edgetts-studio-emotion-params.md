# EdgeTTS-Studio 情绪参数参考

摘自 EdgeTTS-Studio GitHub 仓库（https://github.com/markwatson/EdgeTTS-Studio），验证通过的情绪参数映射。

## 核心发现

edge-tts 的 `Communicate()` 原生支持 `rate` 和 `pitch` 参数，但 **SSML 标签被 edge-tts 的 `escape()` 函数转义**（`<speak>` 变 `&lt;speak&gt;`），因此不能通过 SSML 传入情感标签。正确方案是分段调用 Communicate 参数。

## 情绪 → rate/pitch 映射

| 语气 | rate | pitch | 效果 | 文案示例 |
|:----:|:----:|:-----:|------|---------|
| 平静 | -15% | -3Hz | 略慢沉稳，适合叙述开头/结尾 | 日常叙述、背景交代 |
| 恐惧 | -5% | +5Hz | 稍快+高音，紧张颤抖感 | 鬼魂出现、突然惊吓 |
| 愤怒 | +20% | +8Hz | 快+高，急切暴躁 | 怒骂、争吵、威胁 |
| 悲伤 | -20% | -5Hz | 慢+低，沉重忧郁 | 死亡、离别、回忆 |
| 轻声 | -10% | +0Hz | 略慢，常速音高 | 低语、内心独白 |
| 尖锐 | +10% | +10Hz | 快+高，尖利紧张 | 尖叫、惊恐、高潮 |

## 参数范围

- **rate**: -50% ~ +200%
- **pitch**: -20Hz ~ +20Hz

超出范围会导致 edge-tts 返回错误或音质劣化。

## 调用方式

```python
import edge_tts

# 分段生成（推荐）
communicate = edge_tts.Communicate(
    text="你的故事文本",
    voice="zh-CN-YunyangNeural",
    rate="-15%",
    pitch="-3Hz"
)
await communicate.save("output.mp3")
```

## 拼接方式

各段独立生成后，用 FFmpeg concat demuxer 无损拼接：

```bash
# 准备concat列表
echo "file 'seg_001.mp3'" > concat.txt
echo "file 'seg_002.mp3'" >> concat.txt
...

# 无损拼接（-c copy = 无需重新编码）
ffmpeg -y -f concat -safe 0 -i concat.txt -c copy output.mp3
```

## 注意事项

1. **禁止后处理**：情感已打在 TTS 生成层，再走 FFmpeg volume/aecho/equalizer 会破坏情感
2. **合并相邻同语气段**：减少 TTS 调用次数，拼接更顺滑
3. **音量归一**：生成后用 loudnorm 统一全场音量（可选），不会破坏情感
4. **edge-tts 版本**：参数支持在 edge-tts ≥ 6.0 版本已稳定，无需额外依赖
