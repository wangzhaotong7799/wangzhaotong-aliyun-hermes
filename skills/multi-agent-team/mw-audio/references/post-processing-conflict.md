# ⚠️ 后处理与情感TTS冲突 — 诊断记录

## 问题现象

情感rate/pitch生成的TTS效果好，但最终输出声音不对——情感平淡、音频失真、结尾缺失。

## 根本原因

情感TTS生成后，**又被旧的 `apply_voice_processing()` 后处理覆盖**：

1. edge-tts 生成带情感（rate=-15%, pitch=-3Hz）的 MP3 ✅
2. `apply_voice_processing()` 再用 FFmpeg 做后处理 ❌
   - `volume=5.0` — 大幅放大，引入削波失真
   - `aecho=...` — 回声/混响，冲掉音高变化
   - `equalizer` — EQ 改变频段平衡
3. 最终输出 = 后处理的破坏版本，不是原来的情感TTS

## 代码定位（v7 脚本）

```python
# main() 中 第1294~1304行：

# 2. 生成配音（带情感）✅
if has_tags:
    duration = await generate_emotional_audio(...)

# 3. ❌ 这条线总是在情感TTS之后运行，毁掉一切！
processed_audio = AUDIO_DIR / f"{story_path.stem}_processed.wav"
final_audio_path_str = apply_voice_processing(raw_audio, processed_audio)
```

**修复方法**：当 `has_tags=True` 时，直接跳过第3步：

```python
if has_tags:
    duration = await generate_emotional_audio(...)
    final_audio_path = raw_audio  # 情感TTS不经过后处理！
else:
    duration = await generate_audio(...)
    final_audio_path_str = apply_voice_processing(raw_audio, ...)
```

## 验证方法

```bash
# 对比情感TTS原始音频 和 后处理音频的时长/频谱
ffprobe -v error -show_entries format=duration seg_000.mp3  # 情感段
ffprobe -v error -show_entries format=duration processed.wav  # 后处理版

# 情感TTS + 后处理 = 变短或变糊
# 情感TTS + 无后处理 = 正常时长
```

## 相关文件

- `generate_horror_video_v7.py` — `apply_voice_processing` (line 461) 含 volume=5.0 + equalizer + aecho
- `generate_horror_video_v7.py` — main() 第 1301-1304 行无条件执行后处理
