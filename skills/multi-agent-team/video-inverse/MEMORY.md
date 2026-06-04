---
name: 影墨总指挥
author: wangzhaotong7799
created: 2026-05-15
version: 1.0.0
---

# 🎬 影墨总指挥的工作记忆

## 一、基本信息
- **所属团队**: 影墨小队
- **下辖**: 帧捕手、画师、执笔
- **创建日期**: 2026-05-15
- **工作目录**: /root/wangzhaotong-hermes/videos/

---

## 二、经验记录

### Frame Catcher (帧捕手)
- scene_detect + select_every_n_frame 是关键帧抽取黄金组合
- 4:3横屏视频上下黑边需用 crop 去除，否则影响构图分析

### Prompt Scribe (执笔)
- 翻拍prompt = 2秒钩子框架 + 摄像机百科 + 灯光方案库 + 3秒级时间精度
- 时间点精确到秒（1s-2s, 3s-5s...），模糊描述全毙

### Visual Analyst (画师)
- 色调分析用 dominant_colors + HSV平均值
- Kling 翻拍用 Creative Video Transfer 模式

---

## 三、待办
- [ ] 影墨小队三大件补齐后推送到GitHub
