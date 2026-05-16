# GitHub 参考项目索引 (短视跨平台搬砖)

| 项目 | ⭐ | 可借鉴点 |
|:---|:---:|:---|
| **Fragrant-syllable859/tts-video-generator** | 1 | 中文项目，Word文档→TTS→字幕→视频。骨架直接复用。依赖ElevenLabs API（付费）|
| **SaarD00/AI-Youtube-Shorts-Generator** | 22 | 全自动"无脸"视频流水线：Gemini写脚本→Suno配音→Pexels素材→FFmpeg合成。场景切换和过渡效果值得学 |
| **DarmorGamz/Youtube-Shorts-Generator** | 33 | 用OpenAI生成标题+脚本+TTS+STT→视频组装 |
| **double-k-3033/NR-AI-short-form-video-generator** | 15 | 多智能体架构（Google ADK）: 研究→脚本→资产生成→视频装配→SEO |
| **DarkPancakes/clipforge** | 7 | 逐字动画字幕效果，cinematic效果，一条命令出视频 |
| **bazskos/ai_shorts_generator** | 0 | 纯Python脚本，历史知识类TikTok/Shorts, 用Pexels API找素材 |

## 核心差异

- GitHub项目大多依赖 **ElevenLabs / OpenAI / Gemini API** → 付费
- 本流水线用 **edge-tts**（免费、本地、中文效果好）→ 成本为零
