---
name: short-video-pipeline
description: 自动化"无脸"短视频内容搬砖流水线 — 文本→TTS配音→背景图→字幕→竖版短视频，支持跨平台（抖音/YouTube Shorts/小红书），含手机端视觉优化
version: 4.0.0
author: wangzhaotong7799
tags: [video-generation, tts, content-arbitrage, faceless-video, ffmpeg, bgm-generation]
toolsets_required: [terminal, file, skills]
category: creative
metadata:
  priority: medium
  permission_level: read-write
  current_script: scripts/generate_horror_video_v7.py
  bgm_script: scripts/generate_horror_bgm.py
  final_voice: zh-CN-YunyangNeural
  real_bgm_dir: audio/
  cover_edit_script: references/pillow-image-editing.md
---

# 🎬 自动化短视频搬砖流水线 v3.2 (夜半低语)

> **用途**: 素材源抓取 → 转成短视频 → 发布到目标平台（搬砖副业）
> **品牌名**: 夜半低语（🌙 2026-05-15 确定）  
> **风格**: 仿张震讲故事翻版  
> **当前已实现**: 恐怖故事赛道 v10 — 标签驱动情感TTS（edge-tts原生rate/pitch）+ 多BGM交叉淡入淡出 + 智能故事缩写 + 封面可灵AI图 + 手机端独立优化 + 5人搬砖大队全链路（编剧→画师→音频师→导演→推送师）  
> **搬砖大队架构**: ✍️编剧(mw-scribe) → 🎨画师(mw-artist) → 🎙️音频师(mw-audio) → 🎬导演(mw-producer) → 📡推送师(mw-publisher) | 素材跨队调天网 | 全agent独立记忆
> **用户**: 哈尔滨，搬砖副业（纯平台收益模式，不引流到任何产品）
> **用户关系**: 主人（元宝以AI合伙人身份服务）

---

## ⚖️ 铁律

1. **素材版权意识** — 搬砖内容必须做"二次加工"（改写脚本+换配音+换画面），不能纯搬运
2. **平台规格准确** — 各平台视频规格要查证并遵守（抖音≤60s普通，YouTube Shorts≤60s，小红书≤60s）
3. **配音版权** — edge-tts 为微软Azure语音，商用需确认授权范围
4. **先MVP后优化** — 先手动跑通一条完整链路，再逐步自动化，不要一次搭完所有功能
5. **依赖先查** — 新赛道开始前先检查依赖是否就绪（ffmpeg, edge-tts, wqy-microhei-fonts, Pillow）
6. **用户反馈即信号** — 用户说"不好"时，先修视觉/听觉层面的问题（字幕、背景、BGM），再优化功能。用户偏好直接看效果→给反馈→快速迭代
8. **移动端必须单独优化** — 在电脑上显示好的效果，手机上可能完全不行。必须用手机实际测试后再定稿。手机端核心差异: 屏幕小、扬声器低频重、播放器控制条遮挡底部。

### 手机端优化参数（经过实际测试通过的值）

| 参数 | 电脑值 | 手机值（测试通过） |
|:---|:---:|:---:|
| 字幕字号 | 72px | **54px**（72px会超屏） |
| 每段长度 | 28字符 | **20字符**（28字会超屏） |
| 字幕纵向位置 | 底部往上260px | **底部往上420px**（播放器控制条约高300px） |
| BGM音量 | 22% | **10%或关闭**（手机低频重） |
| 语音放大 | 3倍 | **5倍+限幅**（手机喇叭小） |
| 人声增强 | 无 | 3kHz +**6dB**（手机喇叭中高频弱） |

---

## 📋 工作流架构

```
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│ 素材采集层 │ →  │ 内容处理层 │ →  │ 视频制作层 │ →  │ 发布层    │
│          │    │          │    │          │    │          │
│ 小红书/   │    │ 文本清洗  │    │ edge-tts │    │ 抖音     │
│ 豆瓣/    │    │ 脚本改写  │    │ 配音     │    │ YouTube  │
│ 知乎/    │    │ 分段控制  │    │ 背景生成  │    │ Shorts   │
│ Reddit   │    │ 适配方言  │    │ BGM合成  │    │ 小红书   │
│          │    │          │    │ FFmpeg   │    │          │
│          │    │          │    │ 混音+字幕 │    │          │
└──────────┘    └──────────┘    └──────────┘    └──────────┘
```

### 核心技术栈

| 组件 | 工具 | 说明 |
|:---|:---|:---|
| **TTS 配音** | `edge-tts` | 微软Azure语音，中英文多音色，已在 Hermes venv 中 |
| **背景生成** | `Pillow` (Python) | 生成张震风格封面即背景 — **v8**：纯黑底+噪点做旧纹理+烟熏污渍+暗角强化，竖排血红色大字(210px庞门正道标题体)带双层装饰框（暗红细外框+旧金虚线内框）+四角金色装饰点+白色手绘毛边外边框，底部故事名 |
| **BGM生成** | `numpy` + 纯Python合成 | **7层音轨**: 低频嗡鸣+风噪+钢琴旋律+弦乐垫+不和谐音簇+冲击扫频(v7新增)+心跳(可选)。BGM音量**40%**（从18%→40%） |
| **音频混音** | `FFmpeg amix` | `[1:a]volume=0.40[bgm];[0:a][bgm]amix=inputs=2:duration=first` |
| **字幕** | **FFmpeg drawtext** | 指定 `fontfile=` 路径，**72px Noto Sans CJK Black粗体**，白字黑边+阴影，底部居中 |
| **视频合成** | `ffmpeg` | 4.2.10+，循环静态封面背景+混音音频+drawtext字幕 |
| **输出规格** | 1080×1920, 9:16, H.264 + AAC, crf=23 | 抖音/Shorts/小红书通用 |

### v8+ 封面设计进化（参考图风格 — 基于可灵AI封面）
**新方向: 用户提供参考图 → 直接使用 + 微调，不重新画**

> **重要结论**：Pillow画的封面永远不如用户提供的AI生成图。用户说"太丑了"之后，改用可灵AI 3.0生成的封面直接做背景，通过验收。

**第1步：用户提供参考图**（如可灵AI 3.0生成的封面）
**第2步：用Pillow编辑图片**（删除水印、缩放元素、调整位置）
**第3步：直接作为视频背景图**

图片编辑流程看 references/pillow-image-editing.md。

**编辑参数经验（最终通过的值）：**
- 裁剪区域: 左25% 上14% 右75% 下82%（包含"夜伴低语"和白色边框）
- 缩放比例: **50%**（从100%→67%→"还要缩"→50%通过）
- 粘贴位置: **15%高度**（居中→8%→"太靠上"→20%→"好，就这样"→最终15%）

**⚠️ 图片编辑经验教训：**
1. 元素缩放比例不要问"缩多少"，先缩到50%试，用户会反馈"太XX了"
2. 垂直位置从15%起步试，用户说"再往上"就提，说"太靠上了"就降
3. 可灵AI图可能是RGBA模式，先转RGB再编辑

**v8 封面设计详解（原版Pillow方案，已弃用 — 留作回退用）**

封面结构（自上而下）：

```
┌──────────────────────────────────┐
│  白色手绘毛边外边框 (60px margin) │
│                                  │
│     ┌──────┐    ┌──────┐        │
│     │ 夜   │    │ 半   │   ← 竖排│
│     │      │    │      │     交错│
│     │      │    │      │     排列│
│     │ 低   │    │ 语   │        │
│     └──────┘    └──────┘        │
│          — 镜中人 —              │
│                                  │
│          (字幕区域72px)           │
└──────────────────────────────────┘
```

每个字的装饰细节：
- **双层框**: 外层暗红细线(`DARK_RED=(110,10,15)`) + 内层旧金虚线(`OLD_GOLD=(180,150,80)`)
- **四角金点**: 每个字框外四角各一个金色实心圆点（5px直径）
- **描边**: 12层黑色阴影偏移（`(-5,-5)`到`(7,7)`范围），3层厚度
- **配色**: 主字血红色(`BLOOD_RED=(179,0,0)`)，内框旧金色

| 元素 | 值 | 说明 |
|:---|:---:|:---|
| 字号 | 210px | 封面大字（用户说"再放大"后从160→210） |
| 字体 | 庞门正道标题体 | 毛笔飞白（从思源宋体换成毛笔体，用户说"太愣了"才改） |
| 排列 | 左"夜""低" 右"半""语" | 交错排列更有设计感 |
| 外边框 | 白色手绘毛边 | 60px margin，每4px一段+随机抖动3px |
| 底部文字 | `— 镜中人 —` | 52px，白色，距底部320px |

---

## 🗣️ 情感配音（v10 核心升级 — 2026-05-15）

### ⚠️ [已弃用] SSML 情感标签 — 被 edge-tts 破坏

**2026-05-15 已确认不可用**：edge-tts 7.2.8 内部对所有文本调用 `xml.sax.saxutils.escape()`，将 XML 标签转义为 `&lt;` / `&gt;`，SSML 标签被 TTS 当成普通文字朗读（1027字故事从195s暴增至333s，且念出"http"等URL文本）。

详细分析见 `mw-audio` 技能 或 `references/edge-tts-ssml-limitation.md`（已在多个实验中证实，不再重试）。

### ✅ [正确方案] 标签驱动分段 TTS（edge-tts 原生 rate/pitch）

**原理**：编剧标注的 `[语气｜配乐｜画面]` 标签 → 每段独立调用 `edge_tts.Communicate(text, voice, rate, pitch)` → FFmpeg concat demuxer 无损拼接。

**为什么这个方案对**（前两次错误尝试的教训）：
1. ❌ SSML → edge-tts 内部 escape() 破坏标签（2026-05-15 证实）
2. ❌ FFmpeg atrim+echo/concat → 音量忽大忽小 + 拼接咔哒声（用户明确否决）
3. ✅ edge-tts 原生 rate/pitch → 情绪直接打在 TTS 生成层，不依赖后处理，音质无损

**情绪参数映射**（参考 EdgeTTS-Studio @ sunnyvucs/EdgeTTS-Studio）：

| 语气 | rate | pitch | 听觉效果 |
|:----:|:----:|:----:|---------|
| 平静 | -15% | -3Hz | 略慢沉稳，叙述基调 |
| 恐惧 | -5% | +5Hz | 稍快+高音，颤抖紧张感 |
| 愤怒 | +20% | +8Hz | 快+高，急切暴躁 |
| 悲伤 | -20% | -5Hz | 慢+低，沉重忧郁 |
| 轻声 | -10% | +0Hz | 略慢，常速音高 |
| 尖锐 | +10% | +10Hz | 快+高，尖利紧张 |

**工作流**：
1. 编剧产出：`[平静｜悬疑｜深夜坟场] 李大爷是个坟地管理员...`
2. 音频师解析标签 → 合并相邻同语气段
3. 每段调用 `edge_tts.Communicate(text, voice, rate, pitch)`
4. FFmpeg concat demuxer 拼接（`-c copy` 无损）
5. 全局语音后处理（volume=5.0, alimiter, eq — 无aecho）

**代码实现**（已集成到 `generate_horror_video_v7.py`）：
```python
async def generate_emotional_audio(tagged_segments, voice, output_path):
    """按语气标签分段生成带情绪的TTS"""
    for seg in tagged_segments:
        tone = seg['tone']
        params = TONE_TO_PARAMS.get(tone, TONE_TO_PARAMS['平静'])
        communicate = edge_tts.Communicate(
            seg['text'], voice,
            rate=params['rate'],
            pitch=params['pitch']
        )
        await communicate.save(f"seg_{i:03d}.mp3")
    
    # FFmpeg concat拼接（无需重新编码）
    ffmpeg -y -f concat -safe 0 -i concat.txt -c copy output.mp3
```

**这段代码在 `generate_horror_video_v7.py` 中已完整实现**，支持自动检测输入文本是否含标签。（无标签则回退传统平面TTS，保持向后兼容。）

**关键发现来源**：GitHub 项目 `sunnyvucs/EdgeTTS-Studio` — 研究其 `_apply_emotion()` 函数和 `EMOTION_PRESETS` 映射了解正确的 rate/pitch 用法。

**⛑ 备选方案：rate/pitch/volume 参数 + FFmpeg后处理**

当需要简单全局调整时的降级方案：

#### 步骤1: Communicate参数调全局音色

```python
communicate = edge_tts.Communicate(
    text, "zh-CN-YunjianNeural",
    rate="-5%",    # 语速减慢5% (范围: -50% ~ +50%)
    pitch="-15Hz", # 音高降低15Hz (范围: -50Hz ~ +50Hz)
    volume="+10%"  # 音量提高10%
)
```

| 参数 | 安全范围 | 建议值 |
|:---|:---:|:---:|
| `rate` | -50% ~ +50% | -5% ~ -15%（越慢越恐怖） |
| `pitch` | -50Hz ~ +50Hz | -15Hz ~ -45Hz（越低越深沉） |
| `volume` | -50% ~ +50% | +10% ~ +30% |

**⚠️ 避坑**: pitch="-60Hz" → `NoAudioReceived` 错误！不要超过 -50Hz。

#### 步骤2: FFmpeg后处理

**关键用户反馈：不要过度低沉。** v5/v6 用音高下移22%时用户说"声音太低沉了"。v7改用equalizer低频增强（不做音高下移），用户通过。

**关键用户反馈：音量要足够大。** volume=3.0→"还小"→volume=5.0+alimiter→"还小"→最终通过。手机扬声器需要比电脑大得多的音量。

**关键用户反馈：像播放新闻。** 从 YunjianNeural（深沉男声）换成 **YunyangNeural（成熟男声）** + 减少低音（8dB→4dB）+ 加重混响（40%→60%），听起来更自然、不那么播音腔。

**推荐恐怖故事配音参数（2026-05-15 最终通过版本）：**

```python
voice = "zh-CN-YunyangNeural"  # 成熟男声（不是YunjianNeural！）
af = (
    "volume=5.0,alimiter=limit=0.9,"          # 放大5倍+限幅防失真
    "equalizer=f=80:t=q:w=1.5:g=4,"           # 低音增强4dB（不要太重）
    "equalizer=f=3000:t=q:w=1:g=6,"           # 3kHz人声清晰度（手机喇叭也能听清）
    "aecho=0.08:0.30:1:0.5,"                  # 回声+混响（加重空间感）
    "apad=pad_dur=1.5"                        # 尾部补静音防截断
)
```

**方案A: rubberband 滤镜（如可用）** - 服务器通常没有
```python
af = f"rubberband=pitch=0.92:tempo=1.0,equalizer=f=80:t=q:w=1.5:g=5,aecho=0.06:0.20:1:0.5"
```

**方案B: equalizer + aecho + apad（rubberband不可用时）** — CentOS 8默认FFmpeg
```python
af = f"volume=5.0,alimiter=limit=0.9,equalizer=f=80:t=q:w=1.5:g=8,equalizer=f=3000:t=q:w=1:g=6,aecho=0.06:0.20:1:0.5,apad=pad_dur=1.5"
```

**⚠️ 音量经验教训：用户说"声音小"不能只加一点。** 从3倍→5倍+limiter才通过。手机扬声器需要**大幅**提升音量。使用`alimiter=limit=0.9`防止削波失真。

**结论：恐怖故事配音追求"厚实有压迫感"而非"低沉到模糊"。**
推荐参数：volume=5.0 + alimiter + 低频增强6-8dB + 3kHz人声增强6dB + 回声延迟0.05-0.06s + 回声衰减0.20-0.25。

#### 常见声音效果配方

| 想要的效果 | 滤镜组合 | 适用场景 |
|:---|:---|:---|
| **厚实有压迫感**（v7推荐） | `equalizer=f=80:t=q:w=1.5:g=8,aecho=0.06:0.20:1:0.5` | 恐怖故事标准声线 |
| **轻微低沉+沙哑** | `rubberband=pitch=0.92,equalizer=f=80:g=6,aecho` | 需要适度低沉效果 |
| **极深洞穴音** | `rubberband=pitch=0.85,equalizer=f=80:g=10,aecho=0.9:0.8:80:0.3` | 鬼魂/地狱音效 |
| **电台/电话音** | `equalizer=f=300:g=5,equalizer=f=3000:g=5,equalizer=f=100:g=-8,equalizer=f=8000:g=-20` | 电话对话场景 |

### ❌ 不要尝试逐句调用edge-tts（限流问题）

第5句后出现 `NoAudioReceived`（Azure TTS服务端限流）。✅ **一次调用生成整段 → FFmpeg后处理**。

---

## 🔄 真实BGM文件 vs 合成BGM

### ❌ 合成BGM已弃用（用户说"太简陋了"）

Python代码合成的BGM（正弦波+噪音拼凑）已经被用户否决。保留代码作后备，但**默认使用真实BGM文件**。

### ✅ 正确方法：用户下载真实恐怖BGM

**工作流：**
1. 用户从 Pixabay Music (https://pixabay.com/music/) 搜索 `horror` `dark` `ambient`
2. 下载2-7首免费商用BGM（MP3，每首30秒-1分钟足够）
3. 通过飞书发给元宝，或放到 `audio/` 目录
4. 脚本自动从 `audio/` 目录随机选一首做BGM

**BGM混音参数（真实文件）：**

```python
# 真实BGM音量10%（比合成BGM的22-40%低得多）
# 因为真实BGM动态范围大、低频丰满，10%就够了
bgm_volume = 0.10
```

**BGM文件管理：**
```python
# 脚本自动随机选（排除配音文件）
bgm_files = [f for f in glob.glob("audio/*.mp3") 
             if 'sample_horror' not in f and 'yeban' not in f]
chosen = random.choice(bgm_files)
```

**⚠️ 关键教训：** 用户对BGM的要求是"有但不抢戏"。40%→22%→12%→10%→"暂时关掉"——BGM音量宁可保守。先用 `--no-bgm` 跑纯配音版本让用户通过，再逐步加BGM。

**⚠️ BGM文件筛选必须过滤语音文件（重大bug！）：** 
BGM选择逻辑 `glob("audio/*.mp3")` 会扫到 TTS 生成的语音文件（如 `the_old_mirror_raw.mp3`），如果不排除会导致「配音文件被当BGM混音 → 配音重叠重叠、没有真正BGM」。过滤列表必须包含：
```python
bgm_files = [f for f in glob.glob(str(AUDIO_DIR / "*.mp3")) 
             if 'sample_horror' not in f and 'yeban' not in f and 'test' not in f
             and '_raw.mp3' not in f and '_ssml.mp3' not in f]  # ← 必须加！
```

**⚠️ `--title` 只控制封面显示名，不控制故事内容！**
```bash
# 这两个命令看起来像在做同一件事，但内容完全不同！
python script.py --title "老镜子" --story stories/sample_horror.txt   # ❌ 内容还是镜中人
python script.py --title "老镜子" --story stories/the_old_mirror.txt  # ✅ 正确的老镜子故事
```
`--title` 只是drawtext显示的标题文字，故事内容由 `--story` 文件决定。用户发现内容不对时会直接指出来。

**2016-05-15 已下载BGM库（7首）：**
- atlasaudio-horror-ambience-512255.mp3 (2.8MB)
- everything_is_dead-dark-ambient-516343.mp3 (10.2MB)
- everything_is_dead-dark-ambient-soundscape-493696.mp3 (3.0MB)
- leberch-ambient-horror-518292.mp3 (4.5MB)
- leberch-dark-horror-509729.mp3 (3.5MB)
- leberch-dark-horror-510070.mp3 (4.3MB)
- universfield-dark-shamanic-horror-516353.mp3 (2.3MB)

### 🎵 多BGM交叉淡入淡出（v9 核心升级 — 替代单曲循环）

**问题**：单首BGM只有30~120秒，3分钟故事BGM不够用。循环同一首BGM太单调。

**方案**：随机选3~4首真实BGM → FFmpeg `acrossfade` 2秒交叉淡入淡出拼接 → 裁到配音时长。

**实现（combine_bgm_files）：**

```python
def combine_bgm_files(bgm_file_list, target_duration, output_dir, select_count=3):
    """随机选N首BGM，acrossfade拼接，确保总内容≥配音时长"""
    import random as rnd
    rnd.seed(42)  # 固定种子保证同一故事每次选同一组
    
    n_pick = min(select_count, len(bgm_file_list))
    selected = rnd.sample(bgm_file_list, n_pick)
    bgms = [(Path(f), get_duration(f)) for f in selected]
    total_dur = sum(d for _, d in bgms)
    
    # 内容不够→从剩余文件继续加
    remaining = [f for f in bgm_file_list if f not in [str(x[0]) for x in bgms]]
    while total_dur < target_duration and remaining:
        f = rnd.choice(remaining)
        remaining.remove(f)
        bgms.append((f, get_duration(f)))
        total_dur += bgms[-1][1]
    
    # 构建 filter chain
    parts = [f"[0:a]atrim=duration={bgms[0][1]}[bgm0]"]
    for i in range(1, len(bgms)):
        prev = "bgm0" if i == 1 else f"tmp{i-2}"
        out_label = f"tmp{i-1}" if i < len(bgms) - 1 else "out"
        parts.append(f"[{prev}][{i}:a]acrossfade=d=2:c1=tri:c2=tri[{out_label}]")
    
    cmd = ["ffmpeg", "-y"] + all_inputs + [
        "-filter_complex", ";".join(parts),
        "-map", "[out]",   # ← 必须加！否则输出0字节
        "-t", str(target_duration + 0.5),
        "-acodec", "pcm_s16le", "-vn", output_path
    ]
    subprocess.run(cmd, timeout=120)
```

**⚠️ ⚠️ `-map "[out]"` 是必须的（重大坑点！）：** `acrossfade` 的 filter chain 输出标签 `[out]` 要显式映射，否则 FFmpeg 不知道输出哪个流，生成0字节文件。整个 pipeline 会静默失败（assemble_video_v7 里的 ffprobe 拿到 duration=0 → ZeroDivisionError）。

**⚠️ 跨淡化单曲模式兜底：** 如果 BGM 文件不足2首，或拼接失败（输出为0字节），自动回退到单首BGM，由 `assemble_video_v7` 的循环逻辑补时长。`combine_bgm_files` 已内建文件验证与回退。

### 🎵 动态四段式 BGM（v4 核心升级，v9 已被多BGM拼接取代）

用户明确说: **"配景音乐是非常非常关键的，这个音乐决定成败"** — 必须做动态配乐，不是一条BGM循环。

| 段落 | 时长占比 | 情绪 | 乐器/音色 |
|:---|:---:|:---|:---|
| 铺垫 (calm) | 20% | 平静、建立氛围 | 低频嗡鸣45Hz + 微弱风噪 + 零星钢琴单音 |
| 紧张 (building) | 35% | 不安、压迫感递增 | 低频渐强55Hz + 心跳70BPM + 轻微弦乐 |
| 高潮 (climax) | 30% | 恐怖、冲击 | 不和谐音簇(200-900Hz多重叠加) + 音爆 + 冲击扫频 |
| 收尾 (outro) | 15% | 余音渐弱、不安残留 | 和弦泛音 + 指数衰减 |

### BGM 7层音轨（v7升级）

| 层 | 生成函数 | 说明 |
|:---|:---|:---:|
| 1. **低音嗡鸣** | `generate_bass_drone()` | 28/35/42Hz三频叠加+次谐波，v7加强版 |
| 2. **风噪声** | `generate_wind_noise()` | 低通白噪+LFO调制，v7更明显 |
| 3. **钢琴旋律** | `generate_horror_piano()` | A小调音阶，指数衰减包络，v7密度提升 |
| 4. **弦乐垫** | `generate_string_pad()` | 和弦合成+锯齿波混合，v7加强版 |
| 5. **不和谐音簇** | `generate_atonal_swell()` | 4-7频率随机叠加，v7加强版 |
| 6. **💥 冲击扫频** | `generate_impact_sweeps()` | **v7新增**！3-6次扫频(40→1200Hz)，恐怖片冲击波效果 |
| 7. **💓 心跳** | `generate_heartbeat()` | 68BPM起步，逐步加快30%（恐怖片经典手法） |

### BGM混音参数（v8更新 — 听到配音比震撼更重要）

**关键用户反馈迭代史：**
- v3: BGM音量 18% → 用户说"听不到"
- v7: 提升到 **40%** → 用户说"听到了但配音听不清了"
- v8: **降回22%** → 用户说"好" ✅

**核心原则：配音清晰度优先于BGM震撼度。** 22%是配音和BGM的最佳平衡点。

```bash
ffmpeg -i voice.wav -i bgm.wav \
  -filter_complex "[1:a]volume=0.22[bgm];[0:a][bgm]amix=inputs=2:duration=first[out]" \
  -map "[out]" mixed.wav
```

**⚠️ 不要盲目提升BGM音量！** 40%虽然震撼但压住了配音，用户反馈说"声音太小听不到"。关键是配音穿透力，不是BGM音量。

---

## 🔧 安装与准备（Alibaba Cloud Linux 3 / CentOS 8）

### 字体安装（重要 — 分三步）

**第一步：系统包管理器安装（基础黑体）**
```bash
dnf install -y wqy-microhei-fonts              # 文泉驿微米黑
dnf install -y google-noto-sans-cjk-ttc-fonts  # Noto Sans CJK（7个字重）
```

**第二步：100font免费商用大礼包（63个字体，369MB）**
从 https://www.100font.com/ 下载「免费商用简体中文 必备字体」压缩包，解压到 `/usr/share/fonts/100font/`，运行 `fc-cache -fv`。

**第三步：庞门正道标题体（毛笔飞白，封面专用）**
从 https://www.100font.com/ 搜索 "庞门正道标题体" 下载，解压到 `/usr/share/fonts/100font/`。

 **⚠️ 中文文件名乱码问题**：从100font下载的zip解压后，中文文件名在Linux上显示为乱码（编码问题）。必须：
1. 用 `fc-list | grep` 找到实际文件名（fc-list会正确显示字体名）
2. **创建符号链接**方便脚本引用：
   ```bash
   # 先找到实际文件路径
   fc-list | grep "PangMenZhengDao" | head -1 | awk '{print $1}' | sed 's/:$//'
   # 创建符号链接
   ln -sf "<实际乱码路径>" /usr/share/fonts/100font/PangMenZhengDao-Regular.ttf
   ```
3. 代码中引用符号链接路径，避免写死乱码文件名

**已安装字体家族（全部免费商用）:**

| 字体家族 | 说明 | 封面大字用途 | 路径 |
|:---|:---|:---:|:---|
| **庞门正道标题体** | ⭐毛笔飞白，粗犷有艺术感 | **封面首选** 210px | `/usr/share/fonts/100font/PangMenZhengDao-Regular.ttf`（符号链接） |
| **SourceHanSerifCN** (思源宋体) | 7字重，衬线体，古典正式 | ❌ 已弃用（太愣了） | `/usr/share/fonts/100font/SourceHanSerifCN-Heavy.otf` |
| **SourceHanSansCN** (思源黑体) | 7字重 | 备选 | `/usr/share/fonts/100font/SourceHanSansCN-*.otf` |
| **Alibaba PuHuiTi** (阿里巴巴普惠体) | 10字重，含Black | 备选Black | `/usr/share/fonts/100font/AlibabaPuHuiTi-3-115-Black.otf` |
| **HarmonyOS Sans SC** (鸿蒙) | 6字重 | 备选 | `/usr/share/fonts/100font/HarmonyOS_Sans_SC_Black.ttf` |
| **MiSans** (小米) | 11字重 | 备选 | `/usr/share/fonts/100font/MiSans-Heavy.otf` |
| **HONOR Sans CN** (荣耀) | 9字重 | 备选 | `/usr/share/fonts/100font/HONORSansCN-*.ttf` |
| **OPlusSans3** (一加) | 5字重 | 备选 | `/usr/share/fonts/100font/OPlusSans3-*.ttf` |
| **vivoSans** | 10字重 | 备选 | `/usr/share/fonts/100font/vivoSans-*.ttf` |
| **Noto Sans CJK** (已装) | 7字重 | **字幕专用** NotoBlack 72px | `/usr/share/fonts/google-noto-cjk/NotoSansCJK-Black.ttc` |

### 其余依赖安装

```bash
# 1. ffmpeg（必须从 RPM Fusion 安装）
dnf install -y --nogpgcheck https://mirrors.rpmfusion.org/free/el/rpmfusion-free-release-8.noarch.rpm
dnf install -y --nogpgcheck ffmpeg

# 2. Python 依赖
/root/.hermes/hermes-agent/venv/bin/pip3 install edge-tts pillow numpy

# 3. 工作目录
mkdir -p ~/horror-pipeline/{stories,audio,images,videos,scripts}
```

---

## 🏗️ 当前脚本（v8）

**核心脚本: `scripts/generate_horror_video_v7.py`**（夜半低语 v7/v8，含张震风格封面+震撼BGM+大字幕）
**旧脚本: `scripts/generate_horror_bgm.py`**（BGM生成器，可独立运行）
**退役脚本: `scripts/yeban_v4.py`**（v4/v5/v6旧版，已不推荐使用）
**退役脚本: `scripts/generate_horror_video.py`**（v0.2旧版，已不推荐使用）

功能一览（v8完整实现）:
- [x] 输入 `.txt` 恐怖故事 → 自动生成竖版短视频（25-30秒）
- [x] 文本清洗（去空格、控制长度118字、按标点自然断句9段）
- [x] edge-tts 整段一次配音（YunjianNeural深沉男声）
- [x] FFmpeg后处理：equalizer低频增强8dB + aecho混响回声 + apad防截断
- [x] 张震风格封面即背景（纯黑做旧+竖排庞门正道大字210px+双层装饰框+金角+白边框）
- [x] 七层震撼BGM（低频嗡鸣+风噪+钢琴+弦乐+不和谐音+冲击扫频+心跳40%音量）
- [x] 大字幕72px Noto Black粗体（白字黑边+阴影，**居中偏上**(h-text_h)/2-150，避开底部播放器控制条）
- [ ] 批量处理（一次性处理N个故事）
- [ ] 素材自动采集（需解决抖音下载cookies问题）

使用:
```bash
cd ~/horror-pipeline && python3 scripts/generate_horror_video_v7.py --title "镜中人" [--heartbeat] [--no-bgm]
```

### BGM 生成器（独立使用）

```bash
# 完整配乐（含冲击扫频）
python3 scripts/generate_horror_bgm.py --duration 30 --heartbeat
python3 scripts/generate_horror_bgm.py --duration 30 --style melodic   # 偏旋律
python3 scripts/generate_horror_bgm.py --duration 30 --style ambient    # 纯氛围
```

---

## 🌙 夜半低语 品牌化

### 用户偏好（必须遵守 — 来自用户反馈的铁则）

| 项目 | 用户反馈历史 | 当前最终值 |
|:---|:---|:---:|
| **封面字体** | 思源宋体→"太愣了"→换庞门正道标题体→通过 | **庞门正道标题体**毛笔飞白 |
| **封面大字** | 从160px→"再放大"→210px（Pillow方案）→用户提供可灵AI图→缩小到50% | **直接用可灵AI图**，配套边框缩小1/2 |
| **BGM音量** | 15%→18%→40%→"配音听不清"→22%→通过(电脑)→手机12%还听不清→关闭 | **默认关闭(--no-bgm)**，加BGM前必须先问用户 |
| **语音风格** | 音高下移22%→"太低沉"→改equalizer 8dB→通过 | **厚实有压迫感**，不做音高下移 |
| **语音音量** | 3倍→"还小"→5倍+限幅 | **volume=5.0,alimiter=limit=0.9** |
| **字幕大小(电脑)** | 48px→64px→72px | **72px** Noto Black粗体 |
| **字幕大小(手机)** | 72px→"超屏"→54px，每段≤20字 | **54px**，每段≤20字符 |
| **字幕位置(电脑)** | 底部→"进度条挡住"→底部往上260px→通过 | **y=h-text_h-260**（底部往上260px） |
| **字幕位置(手机)** | 底部→居中→底部往上420px→"超出屏幕"→y=h-text_h-420 还要居中 | **y=h-text_h-420** 或 **y=(h-text_h)/2**，视用户反馈切换 |
| **封面来源** | Pillow画→"太丑了"→改用可灵AI图直接做背景→通过 | **用户提供参考图**直接编辑后使用 |
| **封面布局** | 竖排交错210px→用户发参考图→单列竖排+整体白框→"再缩小1/3"→"边框太大再缩到1/2"→"位置再往上"→"太靠上"→"好，就这样" | 可灵AI图裁剪(25%~75% x 14%~82%)→缩小到50%→粘贴到15%高度 |
| **字体数量** | 只有Noto→用户说"太少"→去100font下载了63+1个 | **64个字体**可用 |
| **多轮迭代** | 几乎每个参数都经历了2-5轮用户反馈才能通过 | 不要期望一次正确，每次调一个参数，用户说"好"再调下一个 |
| **语音音色** | YunjianNeural→"像播放新闻"→YunyangNeural→通过 | **YunyangNeural**（成熟男声） |
| **语音音量** | 3倍→"还小"→5倍+limiter→"还小"→最终通过 | **volume=5.0,alimiter=limit=0.9** |
| **语音后处理** | 低音8dB+混响40%→"像新闻"→低音4dB+混响60%+3kHz增强6dB→通过 | 低音4dB + 3kHz+6dB + 混响60% + 回声0.08s/0.30 |
| **BGM类型** | Python合成→"太简陋了"→用户下载真实BGM | **使用真实BGM文件**（7首），合成BGM已弃用 |
| **BGM音量(手机)** | 40%→22%→12%→10%+真实BGM→18%→很棒 | **18%**（真实BGM动态范围大，不用太高） |
| **字幕大小(手机)** | 72px→超屏→54px，每段≤20字 | **54px**，每段≤20字符 |
| **字幕位置(手机)** | 底部→居中→底部往上420px→超出屏幕→最终420px | **y=h-text_h-420**（避开播放器控制条） |
| **封面来源** | Pillow画→太丑了→改用可灵AI图直接做背景→通过 | **用户提供参考图**直接编辑后使用 |
| **封面布局** | 竖排交错210px→用户发参考图→单列竖排+整体白框→再缩小1/3→边框太大再缩到1/2→位置再往上→太靠上→好就这样 | 可灵AI图裁剪25%-75% x 14%-82%→缩小到50%→粘贴到15%高度 |
| **封面缩小** | 原图→缩到67%→还要缩→缩到50%→通过 | **50%**（从原图裁剪后缩小） |
| **封面上移** | 居中→8%→太靠上→20%→好→15% | **15%高度**粘贴 |
| **故事名装饰** | 白色96px Noto+装饰线→用户说移装饰线+改血红色+改庞门正道→从#B30000调至#B10000→从72px恢复96px→通过 | **庞门正道标题体** #B10000 96px，无装饰线，保留 `— 故事名 —` |

### 视觉层级与故事名装饰（v2 更新 — 2026-05-15）

视频画面从上到下的视觉层级必须分明：

```
┌───────────────────────┐
│    夜  半  低  语       │  ← 层级1: 系列名（封面大字，血红色庞门正道）
│                       │
│                       │
│   — 老镜子 —           │  ← 层级2: 故事名（独立、无装饰线）
│                       │     血红色 #B10000，庞门正道96px
│                       │     ❌ 不要装饰线（用户明确说出装饰线了）
│                       │     ❌ 不要白色（用户说改红色，与系列名同色）
│                       │     ❌ 不要Noto/死板字体（用户说太死板）
│                       │     ❌ 不要72px（用户说缩小后又改回96px）
│                       │
│   字幕内容...           │  ← 层级3: 字幕（白色Noto Black 54px手机/72px电脑）
└───────────────────────┘
```

**故事名字体规则（用户反馈确认 — 2026-05-15）：**
1. 颜色必须与「夜伴低语」一致 → 血红色 **`#B10000`**（不可用白色/灰色，此前迭代从 #B30000 微调至 #B10000 通过）
2. 字体必须用**庞门正道标题体**（毛笔飞白，不死板），不要用Noto无衬线体
3. 字号 **96px**（不是72px！用户从96→72后又要求改回96）
4. **绝对不要装饰线**（用户明确说「出装饰线了」= 去掉上下横线，故事名独立显示）
5. 保留 `— 故事名 —` 两侧短横装饰

❌ `send_message(message="MEDIA:/path/to/file")` — **对飞书不可用**（仅TG/Discord/Matrix支持）

### ✅ 正确方法：通过 Feishu Open API 发送文件

**注意**：飞书不支持 `send_message(message="MEDIA:/path/file")`，必须走 Feishu Open API。

#### 上传图片

```python
import json, requests

# 1. 获取 token
r = requests.post('https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal',
    json={'app_id': APP_ID, 'app_secret': APP_SECRET})
token = r.json()['tenant_access_token']

# 2. 上传图片
with open('cover.jpg', 'rb') as f:
    r2 = requests.post('https://open.feishu.cn/open-apis/im/v1/images',
        headers={'Authorization': f'Bearer {token}'},
        files={'image': ('cover.jpg', f.read(), 'image/jpeg')},
        data={'image_type': 'message'})
img_key = r2.json()['data']['image_key']

# 3. 发送图片消息
requests.post('https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=open_id',
    headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'},
    json={'receive_id': 'ou_xxx', 'msg_type': 'image',
          'content': json.dumps({'image_key': img_key})})
```

#### 上传文件（视频/音频）

⚠️ **关键坑点**：`file_type` 必须用 `stream`（不是 `mp4`），否则发消息时会报 `230055` 类型不匹配错误。

```python
import json, requests

# 1. 获取 token
r = requests.post('https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal',
    json={'app_id': APP_ID, 'app_secret': APP_SECRET})
token = r.json()['tenant_access_token']
headers = {'Authorization': f'Bearer {token}'}

# 2. 上传文件 — file_type=stream（不是 mp4！）
with open('/tmp/video.mp4', 'rb') as f:
    files = {'file': ('video.mp4', f, 'video/mp4')}
    data = {'file_type': 'stream', 'file_name': 'video.mp4'}
    r = requests.post('https://open.feishu.cn/open-apis/im/v1/files',
                      headers=headers, data=data, files=files, timeout=120)
file_key = r.json()['data']['file_key']

# 3. 发送文件消息 — msg_type=file
requests.post('https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=open_id',
    headers={**headers, 'Content-Type': 'application/json'},
    json={'receive_id': 'ou_xxx', 'msg_type': 'file',
          'content': json.dumps({'file_key': file_key})})
```

**性能建议**：28MB 视频上传可能超时（60s timeout），先压缩再上传：
```bash
ffmpeg -y -i input.mp4 -c:v libx264 -preset fast -crf 30 -c:a aac -b:a 128k compressed.mp4
# 28MB → ~9.5MB，上传从超时→几秒完成
```

---

## ⚠️ 已知问题 & 避坑

### 1. ffmpeg 滤镜检查
每次处理语音前先检查可用滤镜：
```bash
ffmpeg -filters 2>/dev/null | grep -E "(rubberband|equalizer|aecho|apad)"
```

### 2. edge-tts 路径
必须使用 Hermes venv 的 Python: `/root/.hermes/hermes-agent/venv/bin/python3`。

### 3. 中文字体
- drawtext 必须用 `fontfile=` 指定绝对路径，不能只写字体名
- 100font的zip解压后中文文件名乱码，用 `fc-list | grep` 找实际文件，**创建符号链接**

### 4. ASS vs drawtext 字幕
- ✅ drawtext 指定 `fontfile=` 路径，不依赖 fontconfig，更可靠
- drawtext 文本特殊字符转义: `'` → `\\'`, `:` → `\\:`

### 5. Pillow 图片处理避坑
- `Image.fromarray()` 需要 numpy 数组，不能传 list → 用 `Image.new('L', size).putdata(list)` 替代
- `getdata()` 在 Pillow 14 (2027-10) 将移除，届时用 `get_flattened_data()`
- TTC 字体文件可以直接用 `ImageFont.truetype(path, size)` 加载
- 暗角遮罩正确做法：
  ```python
  v_data = list(vignette.getdata())
  max_v = max(max(rgb) for rgb in v_data) or 255
  mask_data = [int(255 - max(rgb) * 0.5 / max_v * 255) for rgb in v_data]
  mask_img = Image.new('L', (width, height))
  mask_img.putdata(mask_data)
  img = Image.composite(img, Image.new("RGB", ...), mask_img)
  ```

### 6. 素材采集
当前 web_search 可能因额度不可用。抖音下载需要cookies（`yt-dlp` 报"Fresh cookies needed"）。

### 7. edge-tts 不支持 SSML（核心限制）

### 8. 图片编辑避坑
- 可灵AI生成的图片可能是RGBA模式，先转RGB
- 缩放后再裁剪：先按比例缩放到目标高度，再居中裁剪多余宽度
- 中文文件名乱码：用 `fc-list | grep` 找实际路径，建符号链接
- LANCZOS 缩放滤镜效果最好

### ✅ 多BGM拼接 — 用户明确通过（"从头到尾都有声音，拼接的也非常好"）
  
核心思路: 随机选3~4首真实BGM → 按时长排序 → acrossfade 2秒交叉淡入淡出 → 裁到配音时长。用户特别表扬了拼接效果，这是 v9 的核心升级。

**`combine_bgm_files()` 函数完整实现要点：**
- `rnd.seed(42)` 固定随机种子，同故事选同组BGM（可复现调试）
- `select_count=3` 起选，内容不够自动加第4首及以上，追求全体裁都有内容
- 时长检测用独立 `get_dur()` 函数（ffprobe），不依赖文件元数据
- 用 `-t target_duration + 0.5` 截取到配音时长+0.5s余量（避免落帧）
- 失败回退: 输出文件若为0字节 → 回退到单首BGM，由视频合成模块循环补时长

**⚠️ `-map "[out]"` 是必须的（重大坑点）：** acrossfade 的 filter chain 输出标签 `[out]` 必须显式映射，否则 FFmpeg 不知道输出哪个流→生成0字节文件→整个 pipeline 静默失败（ffprobe 拿到 duration=0 → ZeroDivisionError）。

### 情感逐段音频处理 — ❌ 已回滚（音量忽大忽小）
  
尝试对故事按段落情感（calm/fearful/angry/sad）逐段应用不同 FFmpeg 滤镜→ `concat` 拼接，但用户反馈"声音忽大忽小，十分费劲"。回滚原因：
- `atrim` 提取段落 → 不同滤镜（aecho/asetrate+atempo/equalizer）→ 音量归一化不充分
- `aecho` 在不同情感段落间的切换导致音量跳跃
- `asetrate` 改变音高后 resample 引入振幅变化

**教训：** 逐段音频处理比预想的复杂得多。如果要做，需要在所有段落后追加一个 `loudnorm`（EBU R128 响度归一化）滤镜统一音量。当前版本保持全局单一处理链，不做逐段差异化。

### ⚠️ 多BGM拼接避坑

- `acrossfade` 的 filter chain 输出标签 `[out]` 必须用 `-map "[out]"` 映射，否则0字节
- `combine_bgm_files` 要验证输出文件大小（stat().st_size == 0）并回退到单曲
- 拼接耗时可能超过60秒（3首总长3分钟+），`timeout` 设120s
- `rnd.seed(42)` 固定随机种子，保证同一故事每次选同一组BGM（可复现）
- BGM内容不够时长时自动加第4首或更多，不用循环，追求全程有内容
- 单曲兜底：`assemble_video_v7` 保留 BGM 循环逻辑（检测 duration 后再按需 `stream_loop`）

### 9. [已删除 — 替换内容见上方「SSML 标签不可用」章节]

### 10. 故事缩写 vs 截断

不要用 `clean_text` 按字符数硬截断（会导致砍掉故事高潮）。改为智能缩写：
- 若文字 ≤ max_chars（1200）：原文返回
- 若文字 > max_chars：保留开头35% + 结尾55%，中间"……"过渡
- 缩写后若还太长：再缩一次，保结尾优先
- 缩写规则：以句号/问号/感叹号为断点，保证句子完整

### 11. BGM库文件过滤

BGM选择 `glob("audio/*.mp3")` 必须过滤掉 TTS 语音文件，否则「语音文件被当BGM混音→配音重叠+BGM失效」：
```python
bgm_files = [f for f in bgm_files 
             if 'sample_horror' not in f and 'yeban' not in f and 'test' not in f
             and '_raw.mp3' not in f and '_ssml.mp3' not in f]
```

### 12. `--title` vs `--story`

`--title` 只控制 drawtext 显示的标题文字，`--story` 指定故事文件内容。两个参数所指不一致时，用户会发现并指出来:
```bash
python script.py --title "老镜子" --story stories/sample_horror.txt   # ❌ 标题是「老镜子」，内容是「镜中人」
python script.py --title "老镜子" --story stories/the_old_mirror.txt  # ✅ 标题和内容一致
```

### 13. `rubberband` 滤镜不可用（CentOS 8 / Alibaba Linux 3）

情感音频处理中降音高和变速需要特殊滤镜:
- ❌ `rubberband=pitch=0.92:tempo=1.0` — 不可用（FFmpeg 未编译 librubberband）
- ✅ 降音高代用方案: `asetrate=40572,aresample=44100,atempo=1.087`（44100×0.92=40572，atempo补偿变速）
- ✅ 变速代用方案: `atempo=0.93`（单独使用，不影响音高）

使用前检查:
```bash
ffmpeg -filters 2>/dev/null | grep rubberband
```

### 14. 情感音频处理 — 必须用 concat 而不是 amix

❌ `aselect` 选区后 `amix` 合成会截断为最短段的时长（多个 aselect 输出之间不重叠）
✅ `atrim` 提取后 `concat` 拼接保留原始时长

✅ 验证方法: 比较 ffprobe 返回的情感音频时长是否接近原始配音时长（允许 ±5% 偏差）

---

## 📊 性能参考

| 文本长度 | 配音时长 | 输出文件大小 | 总耗时（含BGM） |
|:---:|:---:|:---:|:---:|
| ~118字 | ~25秒 | ~0.6 MB | <60秒 |

视频规格: 1080×1920, H.264 crf=23, AAC 192kbps, BGM WAV 22050Hz 16-bit

---

## 🎯 各平台视频规格

| 平台 | 推荐时长 | 尺寸 | 格式 | 最大文件 |
|:---|:---:|:---:|:---|:---:|
| 抖音 | 15-60秒 | 9:16 竖版 | MP4 | 4GB |
| YouTube Shorts | ≤60秒 | 9:16 竖版 | MP4 | 256GB |
| 小红书 | 15-60秒 | 3:4 / 9:16 | MP4 | 500MB |

---

## 📚 资源

- 主脚本: `scripts/generate_horror_video_v7.py` (v7/v8)
- BGM生成: `scripts/generate_horror_bgm.py`
- Pillow图片编辑: `references/pillow-image-editing.md` (水印删除/元素缩放)
- 工作目录: `~/horror-pipeline/` (stories/ audio/ images/ videos/ scripts/)
- 故事素材源抓取: `references/story-sourcing.md` (meiriyuedu.cn已验证、番茄小说有反爬、采样→提取→入库全流程)
- 团队架构蓝图: `references/team-blueprint.md` (6人内容生产小队—夜半低语，2026-05-15设计，待建)
- 已有故事库: 40篇恐怖短篇在 `stories/` (story_01~story_40)，最佳候选见 references/story-sourcing.md
- 项目根: `/root/wangzhaotong-hermes/horror-pipeline/`