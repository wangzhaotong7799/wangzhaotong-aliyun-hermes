# 搬砖大队全流程编排指引

> 适用于搬砖大队5人组（编剧→画师→音频师→导演→推送师）的协同工作

## 触发条件

主人主动通知（"等我通知再跑"），不得自主启动生产。

## 流水线顺序

```
Scribe (编剧)
  │  输出: stories/story_XX_标题_tagged.txt
  │  格式: [语气｜配乐｜画面描述] 正文
  ↓
Artist (画师)
  │  读取: stories/story_XX_标题_tagged.txt → 提取第3格画面描述
  │  输出: images/scene_01.jpg ~ scene_XX.jpg (wanx-v1, 768x1152)
  │  工具: scripts/wanx_image_gen.py --batch prompts.txt
  ↓
Audio Engineer (音频师)
  │  读取: stories/story_XX_标题_tagged.txt → 提取[语气]标签
  │  输出: audio/story_XX_raw.mp3 (情感rate/pitch TTS)
  │  工具: generate_horror_video_v7.py (内建情感TTS)
  ↓
Producer (导演)
  │  读取: story_tagged.txt + scene_XX.jpg + raw.mp3
  │  检测: IMAGES_DIR/scene_*.jpg 自动匹配段数
  │  输出: videos/yeban_v7_XX.mp4
  │  工具: generate_horror_video_v7.py (assemble_video_v7)
  ↓
Publisher (推送师)
  │  读取: 最终视频
  │  输出: 多平台发布包
```

## 自动检测机制

Producer（assemble_video_v7）在运行时自动检测：
1. `IMAGES_DIR/scene_*.jpg` 是否存在（画师是否出过图）
2. 图片数量是否匹配段落数（scene_images == len(segments)）
3. 匹配 → 多场景图模式；不匹配 → 回退单图模式

## 标签 → 场景图 映射

编剧三段式标签 `[语气｜配乐｜画面描述]`：
- 第1格「语气」→ 音频师
- 第2格「配乐」→ 音频师(BGM)
- 第3格「画面描述」→ 画师(通义万相)

## 常见陷阱

1. **编剧标签文本必须包含scene_描述**，画师才能提取
2. **画师出图命名必须是 `scene_XX.jpg`**，按时间线排序
3. **画师图数和编剧段数必须一致**，否则回退单图
4. **推送师依赖主人授权**，首次接入新平台必须先请示
