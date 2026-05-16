# 🎙️ 音频师 — 情绪参数参考

## 情绪 → edge-tts rate/pitch 映射

基于 EdgeTTS-Studio (sunnyvucs/EdgeTTS-Studio) 的情绪预设方案：

| 语气 | rate_delta | pitch_delta | 效果描述 |
|:----:|:----------:|:-----------:|---------|
| 平静 | -15% | -3Hz | 略慢，沉稳，适合叙述 |
| 恐惧 | -5% | +5Hz | 稍慢但音高微升，颤抖感 |
| 愤怒 | +20% | +8Hz | 快+高，急切暴躁 |
| 悲伤 | -20% | -5Hz | 慢+低，沉重忧郁 |
| 轻声 | -10% | +0Hz | 略慢，常速音高，低音量感 |
| 尖锐 | +10% | +10Hz | 快+高，尖利紧张 |

## edge-tts.Communicate 用法

```python
import edge_tts

# 带情绪的TTS生成
communicate = edge_tts.Communicate(
    text="故事正文",
    voice="zh-CN-YunyangNeural",
    rate="-15%",   # 语速偏移 -50% ~ +200%
    pitch="-3Hz"   # 音高偏移 -20Hz ~ +20Hz
)
await communicate.save("output.mp3")
```

## 注意
- rate 范围: -50% ~ +200%
- pitch 范围: -20Hz ~ +20Hz
- 段与段之间用 FFmpeg concat 拼接
