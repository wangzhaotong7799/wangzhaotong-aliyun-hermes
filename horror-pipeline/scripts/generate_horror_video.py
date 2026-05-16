#!/usr/bin/env python3
"""
恐怖故事短视频生成器 v0.2 - 修复字幕 + 增强背景
==========================================
v0.2 改进:
  - 固定指定中文字体路径 (WQY Micro Hei / Noto Sans CJK)
  - 字幕使用 drawtext 滤镜，直接指定 fontfile
  - 背景从纯黑改为: 暗红渐变 + 雾状纹理 + 暗角效果
"""

import argparse
import asyncio
import math
import os
import random
import re
import subprocess
import textwrap
from pathlib import Path

# ─── 配置 ───────────────────────────────────────────────────
PROJECT_DIR = Path(__file__).resolve().parent.parent
STORIES_DIR  = PROJECT_DIR / "stories"
AUDIO_DIR    = PROJECT_DIR / "audio"
IMAGES_DIR   = PROJECT_DIR / "images"
VIDEOS_DIR   = PROJECT_DIR / "videos"
SCRIPTS_DIR  = Path(__file__).resolve().parent

# 中文字体路径 (确保存在)
CHINESE_FONTS = [
    "/usr/share/fonts/wqy-microhei/wqy-microhei.ttc",
    "/usr/share/fonts/google-noto-cjk/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/google-noto-cjk/NotoSansCJK-Regular.ttc",
]

DEFAULT_VOICE     = "zh-CN-YunjianNeural"   # 深沉男声
DEFAULT_WIDTH     = 1080                     # 9:16 竖版
DEFAULT_HEIGHT    = 1920
FONT_SIZE         = 52                      # 字幕字号

VOICE_STYLES = {
    "zh-CN-YunjianNeural":  "深沉男声 - 最适合恐怖故事 ★推荐",
    "zh-CN-XiaoxiaoNeural": "温柔女声 - 平静讲述风格",
    "zh-CN-YunxiNeural":    "活力男声 - 适合悬疑解说",
    "zh-CN-XiaoyiNeural":   "亲切女声 - 邻家姐姐讲故事",
}


def find_cn_font() -> str:
    """返回第一个可用的中文字体路径"""
    for fp in CHINESE_FONTS:
        if os.path.exists(fp):
            return fp
    raise RuntimeError("找不到中文字体文件！请先安装 wqy-microhei-fonts 或 google-noto-cjk-fonts")


def ensure_dirs():
    for d in [STORIES_DIR, AUDIO_DIR, IMAGES_DIR, VIDEOS_DIR]:
        d.mkdir(parents=True, exist_ok=True)


def clean_text(text: str, max_chars: int = 500) -> str:
    """清洗故事文本"""
    text = re.sub(r'\s+', ' ', text).strip()
    if len(text) > max_chars:
        cut = max_chars
        for punct in '。！？.!?':
            pos = text.rfind(punct, 0, cut)
            if pos > max_chars * 0.6:
                cut = pos + 1
                break
        text = text[:cut]
    return text


def split_into_segments(text: str, max_len: int = 35) -> list:
    """
    将文本分成字幕段，每段不超过 max_len 字符
    在标点处断开，适合竖屏视频
    """
    import textwrap
    # 先用句末标点分句
    sentences = []
    buffer = ""
    for char in text:
        buffer += char
        if char in '。！？.!?' and len(buffer) >= 5:
            sentences.append(buffer.strip())
            buffer = ""
    if buffer.strip():
        sentences.append(buffer.strip())
    
    if not sentences:
        sentences = [text]
    
    # 对每句控制长度，超过max_len的截断
    result = []
    for s in sentences:
        s = s.strip()
        if not s:
            continue
        if len(s) <= max_len:
            result.append(s)
        else:
            # 长句拆分
            parts = textwrap.wrap(s, width=max_len)
            result.extend(parts)
    
    return result if result else [text]


async def generate_audio(text: str, voice: str, output_path: Path) -> float:
    """使用 edge-tts 生成配音音频，返回时长(秒)"""
    import edge_tts
    
    print(f"  🎙️  配音中... 声音={voice}")
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(str(output_path))
    
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(output_path)],
        capture_output=True, text=True
    )
    duration = float(result.stdout.strip() or 0)
    print(f"      音频时长: {duration:.1f} 秒")
    return duration


def create_scary_background(output_path: Path, width: int = DEFAULT_WIDTH,
                            height: int = DEFAULT_HEIGHT, seed: int = None):
    """
    生成恐怖风格背景图 v2
    - 暗红到纯黑的辐射渐变
    - 叠加雾状纹理层
    - 暗角效果
    - 随机血丝/裂纹
    """
    from PIL import Image, ImageDraw, ImageFilter, ImageEnhance
    
    rng = random.Random(seed)
    print(f"  🎨  生成恐怖背景 v2...")
    
    img = Image.new("RGB", (width, height), color=(0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # ─── 1. 辐射渐变 ──────────────────────────────
    # 中心偏上 (通常视觉焦点位置)
    cx, cy = width // 2, height // 3
    
    # 暗红色系渐变
    center_color = (35, 5, 8)       # 暗红
    mid_color    = (18, 3, 5)       # 深红黑
    edge_color   = (2, 1, 2)        # 纯黑偏紫
    
    max_radius = int(math.sqrt(cx**2 + max(cy, height-cy)**2)) + 100
    
    for r in range(max_radius, 0, -1):
        t = r / max_radius
        if t < 0.3:
            r_color = center_color
        elif t < 0.6:
            frac = (t - 0.3) / 0.3
            r_color = tuple(int(a + (b - a) * frac) for a, b in zip(center_color, mid_color))
        else:
            frac = (t - 0.6) / 0.4
            r_color = tuple(int(a + (b - a) * frac) for a, b in zip(mid_color, edge_color))
        
        # 非完美圆形，稍微椭圆+偏移
        rx = r * 1.1
        ry = r * 1.5
        draw.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], fill=r_color)
    
    # ─── 2. 雾状噪点层 ─────────────────────────────
    fog = Image.new("RGB", (width, height), color=(0, 0, 0))
    fog_draw = ImageDraw.Draw(fog)
    
    for _ in range(15000):
        x = rng.randint(0, width - 1)
        y = rng.randint(0, height - 1)
        # 中心区域更多噪点
        dist = math.sqrt((x - cx)**2 + (y - cy*0.7)**2) / max_radius
        if dist > 1.0:
            continue
        intensity = rng.randint(0, max(1, int(25 * (1.0 - dist))))
        fog_draw.point((x, y), fill=(intensity, intensity // 2, intensity // 3))
    
    fog = fog.filter(ImageFilter.GaussianBlur(radius=8))
    img = Image.blend(img, fog, 0.4)
    
    # ─── 3. 暗角强化 ───────────────────────────────
    vignette = Image.new("RGB", (width, height), color=(0, 0, 0))
    v_draw = ImageDraw.Draw(vignette)
    
    for r in range(int(max_radius * 1.5), int(max_radius * 0.4), -1):
        t = (r - max_radius * 0.4) / (max_radius * 1.1)
        if t < 0:
            continue
        alpha = int(255 * min(1.0, t * 0.8))
        v_draw.ellipse([cx - r, cy - r*1.3, cx + r, cy + r*1.3],
                       fill=(alpha, alpha, alpha))
    
    vignette = vignette.filter(ImageFilter.GaussianBlur(radius=30))
    # 用 multiply 混合使边缘更暗
    # 创建蒙版: 边缘区域alpha值低 → 更暗
    v_arr = list(vignette.getdata())
    v_gray = [max(rgb) for rgb in v_arr]
    max_v = max(v_gray) if v_gray else 255
    mask = Image.new('L', (width, height))
    mask.putdata([int(255 - g * 0.6 / max(255, max_v) * 255) for g in v_gray])
    img = Image.composite(img, Image.new("RGB", (width, height), color=(0, 0, 0)), mask)
    
    # ─── 4. 随机裂纹效果 ────────────────────────────
    crack_draw = ImageDraw.Draw(img)
    for _ in range(rng.randint(3, 6)):
        x, y = rng.randint(0, width - 1), rng.randint(0, height - 1)
        length = rng.randint(50, 200)
        angle = rng.uniform(0, 2 * math.pi)
        for step in range(length):
            nx = int(x + step * math.cos(angle) + rng.gauss(0, 3))
            ny = int(y + step * math.sin(angle) + rng.gauss(0, 3))
            if 0 <= nx < width and 0 <= ny < height:
                brightness = rng.randint(5, 15)  # 非常暗的裂纹
                crack_draw.point((nx, ny), fill=(brightness, brightness // 3, brightness // 4))
    
    # ─── 5. 完成——降噪+调暗 ─────────────────────────
    img = img.filter(ImageFilter.GaussianBlur(radius=1))
    enhancer = ImageEnhance.Brightness(img)
    img = enhancer.enhance(0.85)
    
    # 色相偏冷（偏紫蓝）
    pixels = img.load()
    for x in range(width):
        for y in range(height):
            r, g, b = pixels[x, y]
            pixels[x, y] = (max(0, r - 2), max(0, g - 1), min(255, b + 1))
    
    img.save(str(output_path), quality=92)
    print(f"      保存到: {output_path}")
    return str(output_path)


def assemble_video_with_drawtext(audio_path: Path, bg_image_path: Path,
                                  story_segments: list, output_path: Path,
                                  total_duration: float, bgm_path: Path = None) -> bool:
    """
    合成视频 v3 - drawtext字幕 + 可选BGM混音
    """
    print(f"  🎬  合成视频 v3...")
    
    font_path = find_cn_font()
    print(f"      字体: {font_path}")
    
    # BGM混音
    if bgm_path and bgm_path.exists():
        print(f"      背景音乐: {bgm_path.name}")
        mixed_audio = output_path.parent / f"{output_path.stem}_mixed_audio.wav"
        
        # 用FFmpeg混音: BGM音量降到20%，配音保持100%
        mix_cmd = [
            "ffmpeg", "-y",
            "-i", str(audio_path),
        "-i", str(bgm_path),
            "-filter_complex",
            "[1:a]volume=0.18[bgm];[0:a][bgm]amix=inputs=2:duration=first:dropout_transition=2[out]",
            "-map", "[out]",
            "-acodec", "pcm_s16le",
            str(mixed_audio)
        ]
        mix_result = subprocess.run(mix_cmd, capture_output=True, text=True)
        if mix_result.returncode != 0:
            print(f"  ⚠️  BGM混音失败，使用纯配音: {mix_result.stderr[-200:]}")
            final_audio = audio_path
        else:
            final_audio = mixed_audio
            print(f"      混音完成: BGM音量18%")
    else:
        final_audio = audio_path
    
    # 计算每段字幕的显示时间
    total_chars = sum(len(s) for s in story_segments)
    sec_per_char = total_duration / total_chars if total_chars > 0 else 0.25
    
    # 构建 FFmpeg drawtext 滤镜链
    # 每段字幕作为一个单独的 drawtext 滤镜，按时间启用
    filter_parts = []
    
    current_time = 0.0
    for i, seg in enumerate(story_segments):
        seg_duration = len(seg) * sec_per_char
        end_time = current_time + seg_duration
        
        # drawtext enable 条件: between(t, start, end)
        enable_expr = f"between(t,{current_time:.2f},{end_time:.2f})"
        
        # 转义文本中的特殊字符
        text = seg.replace("'", "’").replace(":", "：")
        text = text.replace("\\", "\\\\").replace("'", "\\\\'").replace(":", "\\:")
        
        # 单行字幕，居中底部
        filter_part = (
            f"drawtext=fontfile={font_path}:"
            f"text='{text}':"
            f"fontsize={FONT_SIZE}:"
            f"fontcolor=white:"
            f"bordercolor=black@0.8:borderw=4:"
            f"shadowcolor=black@0.6:shadowx=3:shadowy=3:"
            f"x=(w-text_w)/2:"
            f"y=h-text_h-120:"
            f"enable='{enable_expr}'"
        )
        filter_parts.append(filter_part)
        
        current_time = end_time
    
    # 组合所有滤镜
    if filter_parts:
        vf_chain = ",".join(filter_parts)
    else:
        vf_chain = "copy"
    
    cmd = [
        "ffmpeg", "-y",
        "-loop", "1",
        "-i", str(bg_image_path),
        "-i", str(final_audio),
        "-c:v", "libx264",
        "-tune", "stillimage",
        "-preset", "medium",
        "-crf", "23",
        "-c:a", "aac",
        "-b:a", "192k",
        "-pix_fmt", "yuv420p",
        "-vf", vf_chain,
        "-shortest",
        "-movflags", "+faststart",
        str(output_path)
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"  ❌ FFmpeg 合成失败:")
        # 打印最后500字符错误
        err = result.stderr[-800:]
        print(err)
        return False
    
    file_size = os.path.getsize(str(output_path)) / (1024 * 1024)
    print(f"  ✅ 视频生成成功!")
    print(f"     路径: {output_path}")
    print(f"     大小: {file_size:.1f} MB")
    return True


async def main():
    parser = argparse.ArgumentParser(description="恐怖故事短视频生成器 v0.2")
    parser.add_argument("--story", "-s", type=str, default=None)
    parser.add_argument("--voice", "-v", type=str, default=DEFAULT_VOICE)
    parser.add_argument("--output", "-o", type=str, default=None)
    parser.add_argument("--list-voices", action="store_true")
    parser.add_argument("--bgm", action="store_true",
                        help="添加恐怖背景音乐")
    parser.add_argument("--bgm-style", type=str, choices=["full", "ambient", "melodic"],
                        default="full",
                        help="BGM风格: full(完整配乐), ambient(纯氛围), melodic(偏旋律)")
    parser.add_argument("--heartbeat", action="store_true",
                        help="BGM中加入心跳声（需配合--bgm使用）")
    args = parser.parse_args()
    
    ensure_dirs()
    
    if args.list_voices:
        print("\n📢 推荐的中文恐怖故事配音声音:\n")
        for voice, desc in VOICE_STYLES.items():
            print(f"  {voice:35s} - {desc}")
        return
    
    # 加载故事
    if args.story:
        story_path = Path(args.story)
    else:
        story_path = STORIES_DIR / "sample_horror.txt"
        if not story_path.exists():
            create_story_sample()
    
    if not story_path.exists():
        print(f"❌ 找不到故事文件: {story_path}")
        return
    
    raw_text = story_path.read_text(encoding="utf-8").strip()
    if not raw_text:
        print(f"❌ 故事文件为空")
        return
    
    print(f"\n{'='*60}")
    print(f"  恐怖故事短视频生成器 v0.2")
    print(f"{'='*60}")
    print(f"\n📖 故事: {story_path.name}")
    
    # 1. 清洗 + 分段
    text = clean_text(raw_text, max_chars=500)
    segments = split_into_segments(text)
    print(f"   清洗后: {len(text)} 字, {len(segments)} 段")
    for i, seg in enumerate(segments, 1):
        print(f"      [{i}] {seg}")
    
    # 2. 生成配音
    audio_path = AUDIO_DIR / f"{story_path.stem}.mp3"
    duration = await generate_audio(text, args.voice, audio_path)
    
    # 3. 生成恐怖背景
    bg_path = IMAGES_DIR / f"bg_{story_path.stem}.jpg"
    create_scary_background(bg_path, seed=hash(story_path.name) % 10000)
    
    # 3.5 BGM
    bgm_path = None
    if args.bgm:
        print(f"  🎵 正在准备背景音乐...")
        # 导入BGM生成模块
        import sys as _sys
        _sys.path.insert(0, str(SCRIPTS_DIR))
        from generate_horror_bgm import generate as generate_bgm
        bgm_path = AUDIO_DIR / f"horror_bgm_{args.bgm_style}_{int(duration)+5}s.wav"
        generate_bgm(duration + 5, bgm_path, heartbeat=args.heartbeat, style=args.bgm_style)
    
    # 4. 合成视频
    output_name = args.output or f"{story_path.stem}_v3.mp4"
    output_path = VIDEOS_DIR / output_name
    success = assemble_video_with_drawtext(
        audio_path, bg_path, segments, output_path, duration, bgm_path
    )
    
    if success:
        print(f"\n{'='*60}")
        print(f"  ✅ v3 视频生成完成! (含BGM)")
        print(f"  📁 {output_path}")
        print(f"{'='*60}")
    else:
        print(f"\n❌ 生成失败")


def create_story_sample():
    story = """那是一个雨夜，我独自走在回家的路上。路灯忽明忽灭，地上的积水映着昏暗的光。

经过一条小巷时，我听到身后传来脚步声。回头一看，空荡荡的街道上一个人都没有。

我加快了脚步，那个声音却越来越近。湿冷的空气里，我闻到了一股奇怪的味道。

终于跑到了家楼下，我气喘吁吁地掏出钥匙。就在开门的一瞬间，一只手搭上了我的肩膀。

"你忘记带伞了。"一个温柔的声音在身后响起。

我僵硬地转过身。面前是一个陌生的女人，她全身湿透了，脸色苍白得没有一丝血色。

但她的手上，根本没有伞。
"""
    sample_path = STORIES_DIR / "sample_horror.txt"
    sample_path.write_text(story.strip(), encoding="utf-8")
    print(f"  📝 示例故事已创建: {sample_path}")


if __name__ == "__main__":
    asyncio.run(main())
