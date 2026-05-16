# edge-tts SSML 限制（已验证，v7.2.8）

> **结论：edge-tts 不支持 SSML 传递。所有文本（包括已正确格式化的 SSML）都会被 `escape()` 转义后交给 TTS 服务。**

## 根因

`edge_tts/communicate.py` 第 349 行：

```python
self.texts = split_text_by_byte_length(
    escape(remove_incompatible_characters(text)),  # xml.sax.saxutils.escape()
    4096,
)
```

`xml.sax.saxutils.escape()` 将所有 XML 特殊字符转义：
- `<` → `&lt;`
- `>` → `&gt;`
- `&` → `&amp;`
- `"` → `&quot;`

即使文本以 `<speak` 开头被正确识别为 SSML，其中的 XML 标签仍会被 `escape()` 破坏。

## 现场验证

```python
# 纯文字 TTS → 时长合理（~5字/秒）
communicate = edge_tts.Communicate("李大爷是个坟地管理员。", "zh-CN-YunyangNeural")
# → 4.2s, 25KB

# SSML 文本传给 edge_tts → 标签被 escape，当文字读
communicate = edge_tts.Communicate('<speak version="1.0" xmlns="..."><voice ...>李大爷...</voice></speak>', ...)
# → 21s, 126KB（5x时长，因为标签被当文字念）
```

完整测试结果（2句测试文本）：

| 输入 | 时长 | 大小 | 结论 |
|:---|:---:|:---:|:---|
| 纯文本 | 4.2s | 25KB | 基准 |
| `<speak>` + `<voice>` | 21.1s | 126KB | ❌ 标签被念 |
| `<speak>` + `<mstts:express-as>` | 37.2s | 222KB | ❌ 标签被念 |

## 真实后果

1027字故事：
- 纯 TTS：195s ✅ 正常
- 带 SSML 标签：333s ❌ 暴增 70%

## 替代方案

### 音频后处理（推荐）

按故事段落逐段渲染情感 → 看 SKILL.md 的「逐段FFmpeg音频后处理渲染情感」章节。

### 全局参数调节（粗略）

```python
communicate = edge_tts.Communicate(text, voice, rate="-5%", pitch="-15Hz")
```

## 其他 TTS 方案（待评估）

- **阿里云百炼 TTS** — 可能支持 SSML，需测试
- **CosyVoice** — 阿里通义千问，支持情绪控制
- **Fish Speech** — 开源，支持 GPT-SoVITS 风格迁移
