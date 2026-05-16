# Ken Burns 缓动运镜 — 实现参考

> 让静态图产生缓慢推拉/平移效果，消除"静态幻灯片"感。
> 参考抖音"规则怪谈"类动画（如《医怨》）。

---

## ⚠️ 已知坑点（实测验证）

| 坑 | 症状 | 修复 |
|:---|:-----|:-----|
| `t` 变量在 zoompan x/y 中不可用 | `Undefined constant or missing '(' in 't/...'` | 用 `on`（输出帧编号）替代 `t` |
| `-loop 1` + zoompan | zoompan 生成多余帧或失败 | 只用 `-i img.jpg`，去掉 `-loop 1` |
| zoompan 后接 scale/pad | 画面黑屏或尺寸错误 | **先** scale/pad **后** zoompan |
| zoompan 输出非 yuv420p | H.264 编码警告 | zoompan 后追加 `,format=yuv420p` |
| `-t` 时长参数 + zoompan `d` 参数冲突 | 时长不符合预期 | 去掉 `-t`，只用 zoompan 的 `d=帧数` |
| `-tune stillimage` + zoompan | 编码器优化方向错误 | 去掉 `-tune stillimage` |

---

## 🎯 核心公式

```
FFmpeg 滤镜链顺序（必须遵守）:
  scale=1080:1920:force_original_aspect_ratio=decrease,
  pad=1080:1920:(ow-iw)/2:(oh-ih)/2:color=black,
  zoompan=z='min(1+{rate}*on,{max_zoom})':
           d={帧数}:
           x='iw/2-(iw/zoom/2)+{pan_x}*sin(2*PI*on/{帧数}+{相位})':
           y='(ih/2-(ih/zoom/2))+{pan_y}*sin(2*PI*on/{帧数}+{相位})':
           s=1080x1920:
           fps=24,
  format=yuv420p
```

**关键变量说明：**
- `on` = 输出帧编号（从0开始），不是 `t`（t 在 zoompan 中不可用）
- `zoom` = 当前缩放倍率（zoompan 自动维护的变量）
- `rate` = 每帧缩放增量，例如 `0.0005`（慢）到 `0.002`（快）
- `d` = 总输出帧数 = `clip_dur × fps`

---

## 参数速查表

### 缩放

| 风格 | rate | max_zoom | 适用场景 |
|:----|:----:|:--------:|:---------|
| 极慢推近 | 0.00025 | 1.04 | 平静叙述（10s段） |
| 慢推近 | 0.0005 | 1.06 | 常规场景（5-8s段） |
| 中速推近 | 0.001 | 1.08 | 紧张推进（3-5s段） |
| 急推跳吓 | 0.003 | 1.12 | 高潮段（2-3s段） |

### 呼吸微摆

| 效果 | x表达式 | y表达式 | 适用 |
|:----|:--------|:--------|:-----|
| 轻微呼吸 | `+3*sin(2*PI*on/{总帧数})` | `+1*sin(2*PI*on/{总帧数})` | 平静 |
| 中等晃动 | `+8*sin(2*PI*on/{总帧数})` | `+3*sin(2*PI*on/{总帧数}+1.5)` | 恐惧 |
| 剧烈摇晃 | `+15*sin(2*PI*on/{总帧数})` | `+6*sin(2*PI*on/{总帧数}+1.5)` | 高潮/奔跑 |

**注意**：`2*PI*on/{总帧数}` 形成**一个完整正弦周期**。振幅（前系数）控制晃动幅度。

---

## 💻 实测验证命令

```bash
# 单张图测试 Ken Burns（缩放1.06 + 呼吸微摆）
ffmpeg -y -i scene_01.jpg \
  -vf "scale=1080:1920:force_original_aspect_ratio=decrease,\
       pad=1080:1920:(ow-iw)/2:(oh-ih)/2:color=black,\
       zoompan=z='min(1+0.0005*on,1.06)':\
               d=120:\
               x='iw/2-(iw/zoom/2)+5*sin(2*PI*on/120+0)':\
               y='(ih/2-(ih/zoom/2))+3*sin(2*PI*on/120+0)':\
               s=1080x1920:\
               fps=24,\
       format=yuv420p" \
  -c:v libx264 -preset ultrafast -crf 28 \
  -pix_fmt yuv420p -an test_zoompan.mp4
```

---

## 📝 Python 集成（已验证可用）

在 `generate_horror_video_v7.py` 中替换 scene clip 生成段：

```python
fps = 24
total_frames = max(int(clip_dur * fps), 1)
# 每张图独立随机（可复现种子）
rng = random.Random(ken_seed + idx * 100)
zoom_end = round(rng.uniform(1.04, 1.08), 3)
zoom_step = (zoom_end - 1.0) / max(total_frames, 1)
pan_x_amp = rng.randint(3, 15)
pan_y_amp = rng.randint(1, 6)
pan_x_phase = round(rng.uniform(0, 6.28), 2)
pan_y_phase = round(rng.uniform(0, 6.28), 2)

ken_burns_vf = (
    f"scale=1080:1920:force_original_aspect_ratio=decrease,"
    f"pad=1080:1920:(ow-iw)/2:(oh-ih)/2:color=black,"
    f"zoompan=z='min(1+{zoom_step}*on,{zoom_end})':"
    f"d={total_frames}:"
    f"x='iw/2-(iw/zoom/2)+{pan_x_amp}*sin(2*PI*on/{total_frames}+{pan_x_phase})':"
    f"y='(ih/2-(ih/zoom/2))+{pan_y_amp}*sin(2*PI*on/{total_frames}+{pan_y_phase})':"
    f"s=1080x1920:"
    f"fps={fps},"
    f"format=yuv420p"
)

clip_cmd = [
    "ffmpeg", "-y",
    "-i", str(img_path),       # 不要 -loop 1
    "-vf", ken_burns_vf,
    "-c:v", "libx264",
    "-preset", "ultrafast",
    "-crf", "28",
    "-pix_fmt", "yuv420p",
    "-an",
    str(clip_path)
]
# 不要 -t 参数（zoompan 的 d 控制时长）
# 不要 -tune stillimage
```

**与旧方案对比：**

| 参数 | 旧（静态图） | 新（Ken Burns） |
|:----|:------------|:----------------|
| input | `-loop 1 -i` | `-i` |
| vf | `scale,pad,setsar` | `scale,pad,zoompan...,format=yuv420p` |
| 时长控制 | `-t {clip_dur}` | zoompan `d={total_frames}` |
| tune | `-tune stillimage` | 无 |
| 效果 | 静态卡帧 | 缓慢缩放+呼吸摆动 |

---

## 🎬 进阶技巧

### 视差分层（需要画师提供抠图）

```
前景层 → overlay x='W/2-iw/2+sin(t)*40'  (快速移动)
中景层 → overlay 或 缩放居中              (缓慢缩放)
背景层 → zoompan 或 不动                  (几乎不动)
```

### 跳吓效果

```python
# 急推 + 红色闪屏
vf = (
    f"zoompan=z='1+0.3*on':d=10,"
    f"colorbalance=rs=0.3:gs=-0.2:bs=-0.2,"
    f"fade=in:0:5"
)
```

### 光影闪烁

```python
# 亮度随正弦波变化，配合心跳/BGM节奏
vf = f"eq=brightness='0+0.03*sin(2*PI*on/48+0)':contrast=1.05"
```

---

## 注意事项

1. **zoompan 不支持 `t` 变量**（2026-05实测 FFmpeg 4.x），必须用 `on`（输出帧编号）
2. 缩放上限不建议超过 1.12，否则画质劣化明显
3. 通义万相输出 768x1152，缩放至 1080x1920 已有画质损失
4. 每张图用独立随机种子 + 固定偏移（`seed + idx*100`），确保每次运行一致
5. iPhone/手机端 24fps 已足够流畅，30fps 会增大文件体积
