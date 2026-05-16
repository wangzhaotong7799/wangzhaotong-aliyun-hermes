#!/usr/bin/env python3
"""
夜半低语 - 恐怖故事短视频生成器 v4
===============================
仿张震讲故事风格，三大升级:
  1. SSML动态语音 (语速/音高/停顿随情节变化)
  2. 四段式BGM (铺垫→紧张→高潮→收尾，渐变衔接)
  3. 张震风格封面
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
COVERS_DIR   = PROJECT_DIR / "covers"
SCRIPTS_DIR  = Path(__file__).resolve().parent

CHINESE_FONTS = [
    "/usr/share/fonts/wqy-microhei/wqy-microhei.ttc",
    "/usr/share/fonts/google-noto-cjk/NotoSansCJK-Bold.ttc",
]

DEFAULT_VOICE = "zh-CN-YunjianNeural"
WIDTH, HEIGHT = 1080, 1920


def find_cn_font() -> str:
    for fp in CHINESE_FONTS:
        if os.path.exists(fp):
            return fp
    raise RuntimeError("无中文字体")


def ensure_dirs():
    for d in [STORIES_DIR, AUDIO_DIR, IMAGES_DIR, VIDEOS_DIR, COVERS_DIR]:
        d.mkdir(parents=True, exist_ok=True)


# ═══════════════════════════════════════════════════════════
# 1. 动态语音生成 (逐句调用edge-tts，不用SSML)
# ═══════════════════════════════════════════════════════════

async def generate_story_audio(text: str, output_path: Path) -> float:
    """
    整段文本一次配音 → FFmpeg后期处理压低+沙哑
    简单可靠，避免逐句调用的限流问题
    """
    import edge_tts
    import shutil
    
    print(f"  🎙️  配音生成中... (长度={len(text)}字)")
    
    # 1. 一次调用生成全部配音
    communicate = edge_tts.Communicate(
        text, DEFAULT_VOICE,
        rate="-5%", pitch="-15Hz", volume="+10%"
    )
    await communicate.save(str(output_path))
    
    # 获取原始时长
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(output_path)],
        capture_output=True, text=True
    )
    orig_dur = float(r.stdout.strip() or 0)
    print(f"      原始时长: {orig_dur:.1f}s")
    
    # 2. FFmpeg后处理: 音高下移 + bass增强 + 削高频(暗哑) + 轻微混响
    print(f"      🔊 后期处理: 压低+沙哑...")
    
    sr_r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "stream=sample_rate",
         "-of", "default=noprint_wrappers=1:nokey=1", str(output_path)],
        capture_output=True, text=True
    )
    src_sr = int(sr_r.stdout.strip() or 24000)
    
    processed = output_path.parent / f"{output_path.stem}_processed.mp3"
    
    # 音高下移到92% (轻微低沉) + bass增强 + 高频衰减 + 回声(空间感)
    af = (
        f"aformat=sample_rates={src_sr},"
        f"asetrate={src_sr}*0.92,"
        f"atempo=1/0.92,"
        f"bass=g=4,"
        f"equalizer=f=1500:t=q:w=1:g=-6,"
        f"equalizer=f=4000:t=q:w=1:g=-10,"
        f"aecho=0.8:0.7:40:0.2"
    )
    
    subprocess.run([
        "ffmpeg", "-y", "-i", str(output_path),
        "-af", af,
        "-c:a", "libmp3lame", "-q:a", "2",
        str(processed)
    ], capture_output=True)
    
    shutil.copy(processed, output_path)
    
    # 最终时长
    r2 = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(output_path)],
        capture_output=True, text=True
    )
    duration = float(r2.stdout.strip() or 0)
    
    # 清理
    if processed.exists():
        processed.unlink()
    
    print(f"      ✅ 合成完成: {duration:.1f}s (低沉沙哑版)")
    return duration


# ═══════════════════════════════════════════════════════════
# 2. 四段式动态BGM
# ═══════════════════════════════════════════════════════════

def _note_to_freq(semitones: int, base: float = 110) -> float:
    return base * (2 ** (semitones / 12))


def _sin_wave(freq: float, length: int, sr: int) -> list:
    return [math.sin(2 * math.pi * freq * t / sr) for t in range(length)]


def generate_segment_bgm(duration: float, mood: str, sr: int = 22050) -> list:
    """
    根据情绪生成不同风格BGM片段
    mood: "calm" / "building" / "climax" / "outro"
    """
    n = int(sr * duration)
    result = [0.0] * n
    rng = random.Random(hash(mood) % 10000)
    
    # 所有片段共享的低频嗡鸣
    drone_freqs = {"calm": 45, "building": 50, "climax": 55, "outro": 40}
    drone_freq = drone_freqs.get(mood, 45)
    
    drone = _sin_wave(drone_freq, n, sr)
    drone2 = _sin_wave(drone_freq + 8, n, sr)
    for t in range(n):
        env = min(1.0, t / (sr * 0.3), (n - t) / (sr * 0.3))
        result[t] += (drone[t] * 0.20 + drone2[t] * 0.08) * env
    
    if mood == "calm":
        # 铺垫：微弱风噪 + 偶尔钢琴单音
        for _ in range(rng.randint(2, 4)):
            start = rng.randint(int(sr * 0.5), n - sr)
            freq = _note_to_freq(rng.choice([0, 3, 7, 10]), 130)
            note_len = min(n - start, int(rng.uniform(0.8, 2.0) * sr))
            for i in range(note_len):
                env = math.sin(math.pi * i / note_len)
                result[start + i] += 0.04 * env * math.sin(2 * math.pi * freq * i / sr)
    
    elif mood == "building":
        # 紧张：低频渐强 + 心跳
        for t in range(n):
            env = min(1.0, t / (sr * 1.0)) * min(1.0, (n - t) / (sr * 0.3))
            # 和弦叠加
            saw_val = 2 * (55 * t / sr - math.floor(55 * t / sr + 0.5))
            result[t] += 0.03 * env * (0.5 * math.sin(2 * math.pi * 55 * t / sr) + 0.3 * saw_val)
        # 心跳 (加快)
        bpm = 70
        beat_int = int(60.0 / bpm * sr)
        lb = int(0.07 * sr)
        for bs in range(int(sr), n, beat_int):
            for i in range(lb):
                p = bs + i
                if p < n:
                    result[p] += 0.06 * math.sin(math.pi * i / lb)
    
    elif mood == "climax":
        # 高潮：不和谐音簇 + 强冲击
        for _ in range(rng.randint(3, 5)):
            start = rng.randint(0, n - sr)
            freqs = [rng.uniform(200, 900) for _ in range(rng.randint(3, 6))]
            note_len = min(n - start, int(rng.uniform(0.5, 1.5) * sr))
            for i in range(note_len):
                env = math.sin(math.pi * i / note_len)
                s = sum(math.sin(2 * math.pi * f * i / sr) for f in freqs) / len(freqs)
                result[start + i] += 0.07 * env * s
    
    elif mood == "outro":
        # 收尾：逐渐消失的余音
        chord = rng.choice([[0, 3, 7], [7, 10, 14]])
        for semi in chord:
            freq = _note_to_freq(semi, 130)
            for t in range(n):
                env = math.exp(-t / (sr * 2.0))
                result[t] += 0.03 * env * math.sin(2 * math.pi * freq * t / sr)
    
    return result


def generate_dynamic_bgm(segment_durations: list, moods: list, 
                          sr: int = 22050, crossfade_ms: int = 2000) -> list:
    """
    生成完整的动态配乐
    segment_durations: 每段时长(秒)
    moods: 每段情绪 ["calm","building","climax","outro"]
    """
    assert len(segment_durations) == len(moods)
    
    segments = []
    for dur, mood in zip(segment_durations, moods):
        seg = generate_segment_bgm(dur, mood, sr)
        segments.append(seg)
        print(f"      BGM片段 [{mood:8s}] {dur:.1f}s")
    
    # 拼接 + 交叉淡入淡出
    total_len = sum(len(s) for s in segments)
    result = [0.0] * total_len
    
    cf_samples = int(sr * crossfade_ms / 1000)
    offset = 0
    
    for seg in segments:
        for i, s in enumerate(seg):
            result[offset + i] += s
        offset += len(seg)
    
    # 段间交叉淡入淡出
    if len(segments) > 1:
        offset = 0
        for seg_idx in range(len(segments) - 1):
            seg_len = len(segments[seg_idx])
            for i in range(min(cf_samples, seg_len, len(segments[seg_idx + 1]))):
                t = i / cf_samples
                result[offset + seg_len - cf_samples + i] *= (1 - t * 0.3)
            offset += seg_len
    
    # 归一化
    max_val = max(abs(s) for s in result) or 1.0
    if max_val > 0.8:
        result = [s * 0.8 / max_val for s in result]
    
    return result


# ═══════════════════════════════════════════════════════════
# 3. 张震风格封面
# ═══════════════════════════════════════════════════════════

def generate_cover(title: str, subtitle: str, output_path: Path,
                   width: int = 1080, height: int = 1920):
    """
    生成张震讲故事风格的封面
    - 全黑或暗红渐变背景
    - 大号白色粗体标题 (2-4个字)
    - 下方小字副标题
    """
    from PIL import Image, ImageDraw, ImageFilter, ImageEnhance
    
    print(f"  🖼️  生成封面: {title}")
    
    img = Image.new("RGB", (width, height), color=(5, 3, 5))
    draw = ImageDraw.Draw(img)
    
    # 暗红辐射渐变（中心偏上）
    cx, cy = width // 2, height // 3
    max_r = int(math.sqrt(cx**2 + (height - cy)**2)) + 100
    for r in range(max_r, 0, -3):
        t = r / max_r
        if t > 0.7:
            c = (int(20 * (1 - t)), int(5 * (1 - t)), int(8 * (1 - t)))
        else:
            c = (2, 1, 2)
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=c)
    
    # 文泉驿微米黑
    font_path = find_cn_font()
    
    # 大字标题
    font_size = 140
    from PIL import ImageFont
    font = ImageFont.truetype(font_path, font_size)
    
    # 测量文字宽度
    bbox = draw.textbbox((0, 0), title, font=font)
    tw = bbox[2] - bbox[0]
    
    # 居中绘制
    x = (width - tw) // 2
    y = height // 3
    
    # 文字阴影
    shadow_offset = 4
    draw.text((x + shadow_offset, y + shadow_offset), title, 
              fill=(0, 0, 0, 180), font=font)
    # 主文字
    draw.text((x, y), title, fill=(255, 255, 255), font=font)
    
    # 副标题
    if subtitle:
        sub_font = ImageFont.truetype(font_path, 48)
        sub_bbox = draw.textbbox((0, 0), subtitle, font=sub_font)
        stw = sub_bbox[2] - sub_bbox[0]
        sx = (width - stw) // 2
        sy = y + font_size + 60
        draw.text((sx + 2, sy + 2), subtitle, fill=(50, 50, 50), font=sub_font)
        draw.text((sx, sy), subtitle, fill=(180, 180, 180), font=sub_font)
    
    # 底部水印
    brand_font = ImageFont.truetype(font_path, 36)
    brand_text = "夜半低语"
    br_bbox = draw.textbbox((0, 0), brand_text, font=brand_font)
    btw = br_bbox[2] - br_bbox[0]
    bx = (width - btw) // 2
    by = height - 150
    draw.text((bx, by), brand_text, fill=(80, 20, 20), font=brand_font)
    
    img.save(str(output_path), quality=92)
    print(f"      保存: {output_path.name}")


# ═══════════════════════════════════════════════════════════
# 4. 主流程
# ═══════════════════════════════════════════════════════════

def analyze_story_arc(text: str) -> tuple:
    """
    分析故事结构，返回各段时长比例和情绪
    返回: [(比例, 情绪), ...]
    """
    sentences = [s for s in re.split(r'[。！？.!?\n]', text) if s.strip()]
    total = len(sentences)
    
    if total <= 3:
        return [(0.25, "calm"), (0.35, "building"), (0.25, "climax"), (0.15, "outro")]
    
    # 三段分配
    arcs = [
        (0.20, "calm"),     # 铺垫 20%
        (0.35, "building"),  # 紧张 35%
        (0.30, "climax"),    # 高潮 30%
        (0.15, "outro"),     # 收尾 15%
    ]
    return arcs


async def main():
    parser = argparse.ArgumentParser(description="夜半低语恐怖故事生成器 v4")
    parser.add_argument("--story", "-s", type=str, default=None)
    parser.add_argument("--output", "-o", type=str, default=None)
    parser.add_argument("--title", "-t", type=str, default="夜半低语",
                        help="封面标题")
    parser.add_argument("--bgm", action="store_true", default=True,
                        help="添加动态BGM")
    parser.add_argument("--heartbeat", action="store_true", default=True)
    parser.add_argument("--no-bgm", action="store_true",
                        help="不加BGM")
    args = parser.parse_args()
    
    ensure_dirs()
    
    # 加载故事
    if args.story:
        story_path = Path(args.story)
    else:
        story_path = STORIES_DIR / "sample_horror.txt"
    
    if not story_path.exists():
        print(f"❌ 找不到故事: {story_path}")
        return
    
    raw = story_path.read_text(encoding="utf-8").strip()
    if not raw:
        return
    
    use_bgm = args.bgm and not args.no_bgm
    
    print(f"\n{'='*50}")
    print(f"  🌙 夜半低语 v4")
    print(f"{'='*50}")
    print(f"\n📖 故事: {story_path.name}")
    
    # 1. 生成动态语音 (逐句调用edge-tts)
    audio_path = AUDIO_DIR / f"{story_path.stem}_v4_audio.mp3"
    duration = await generate_story_audio(raw, audio_path)
    
    # 2. 生成动态BGM
    bgm_path = None
    if use_bgm:
        print(f"  🎵 生成动态配乐...")
        arcs = analyze_story_arc(raw)
        seg_durs = [duration * p for p, _ in arcs]
        moods = [m for _, m in arcs]
        
        audio_dir = AUDIO_DIR
        bgm_path = audio_dir / f"dynamic_bgm_{story_path.stem}.wav"
        
        bgm_samples = generate_dynamic_bgm(seg_durs, moods)
        # 保存BGM
        import struct, wave
        with wave.open(str(bgm_path), 'w') as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(22050)
            for s in bgm_samples:
                int_val = int(max(-32768, min(32767, s * 32767)))
                wav.writeframes(struct.pack('<h', int_val))
        print(f"      ✅ BGM保存: {bgm_path.name}")
    
    # 3. 混音 + 合成视频
    print(f"  🎬 合成视频...")
    
    # 混音
    if bgm_path and bgm_path.exists():
        mixed_audio = audio_path.parent / f"{story_path.stem}_mixed.wav"
        mix_cmd = [
            "ffmpeg", "-y",
            "-i", str(audio_path),
            "-i", str(bgm_path),
            "-filter_complex",
            "[1:a]volume=0.35[bgm];[0:a][bgm]amix=inputs=2:duration=first:dropout_transition=2[out]",
            "-map", "[out]",
            "-acodec", "pcm_s16le",
            str(mixed_audio)
        ]
        subprocess.run(mix_cmd, capture_output=True, text=True)
        final_audio = mixed_audio
        print(f"      BGM混音完成 (音量15%)")
    else:
        final_audio = audio_path
    
    font_path = find_cn_font()
    
    # 字幕分段
    sentences = [s for s in re.split(r'[。！？.!?\n]', raw) if s.strip()]
    segments = sentences if sentences else [raw]
    
    # 计算每段字幕时间
    total_chars = sum(len(s) for s in segments)
    sec_per_char = duration / total_chars if total_chars > 0 else 0.2
    
    # 构建drawtext滤镜链
    filter_parts = []
    current_time = 0.0
    for seg in segments:
        seg_dur = len(seg) * sec_per_char
        end_time = current_time + seg_dur
        
        enable = f"between(t,{current_time:.2f},{end_time:.2f})"
        text = seg.replace("'", "’").replace(":", "：").replace("\\", "\\\\").replace("'", "\\'")
        
        fpart = (
            f"drawtext=fontfile={font_path}:"
            f"text='{text}':"
            f"fontsize=56:"
            f"fontcolor=white:"
            f"bordercolor=black@0.8:borderw=3:"
            f"shadowcolor=black@0.6:shadowx=3:shadowy=3:"
            f"x=(w-text_w)/2:"
            f"y=h-text_h-140:"
            f"enable='{enable}'"
        )
        filter_parts.append(fpart)
        current_time = end_time
    
    vf = ",".join(filter_parts) if filter_parts else "copy"
    
    # 生成背景图（暗黑风格）
    bg_path = IMAGES_DIR / f"bg_{story_path.stem}_v4.jpg"
    from PIL import Image, ImageDraw, ImageFilter, ImageEnhance
    
    bg_img = Image.new("RGB", (WIDTH, HEIGHT), color=(5, 3, 5))
    bg_draw = ImageDraw.Draw(bg_img)
    
    # 暗红辐射渐变
    cx, cy = WIDTH // 2, HEIGHT // 3
    max_r = int(math.sqrt(cx**2 + (HEIGHT - cy)**2)) + 100
    for r in range(max_r, 0, -2):
        t = r / max_r
        if t < 0.4:
            c = (int(30 * (1 - t*2)), int(5 * (1 - t*2)), int(8 * (1 - t*2)))
        elif t < 0.7:
            fr = (t - 0.4) / 0.3
            c = (int(30 * (1 - fr) + 8 * fr), 3, int(8 * (1 - fr) + 3 * fr))
        else:
            c = (3, 1, 3)
        bg_draw.ellipse([cx - r, cy - r*1.3, cx + r, cy + r*1.3], fill=c)
    
    bg_img = bg_img.filter(ImageFilter.GaussianBlur(radius=2))
    bg_img.save(str(bg_path), quality=90)
    
    # 生成封面图（片头）
    cover_path = COVERS_DIR / f"cover_{story_path.stem}.jpg"
    story_title = args.title or "夜半低语"
    generate_cover(story_title, "", cover_path)
    
    # 执行合成
    output_name = args.output or f"{story_path.stem}_v4.mp4"
    output_path = VIDEOS_DIR / output_name
    temp_main = output_path.parent / f"{output_path.stem}_main.mp4"
    
    # Step 1: 先合成主视频（含配音+BGM+字幕）
    print(f"  🎬 合成主视频...")
    cmd = [
        "ffmpeg", "-y",
        "-loop", "1",
        "-i", str(bg_path),
        "-i", str(final_audio),
        "-c:v", "libx264",
        "-tune", "stillimage",
        "-preset", "medium",
        "-crf", "23",
        "-c:a", "aac",
        "-b:a", "192k",
        "-pix_fmt", "yuv420p",
        "-vf", vf,
        "-shortest",
        "-movflags", "+faststart",
        str(temp_main)
    ]
    subprocess.run(cmd, capture_output=True, text=True)
    
    # Step 2: 生成3秒片头（封面图 + 开头BGM片段）
    intro_path = output_path.parent / f"{output_path.stem}_intro.mp4"
    
    # 提取前3秒配音作为片头音效（用原始配音，不加BGM以免突兀）
    intro_audio = output_path.parent / f"{output_path.stem}_intro_audio.mp3"
    subprocess.run([
        "ffmpeg", "-y", "-i", str(audio_path),
        "-t", "3", "-c", "copy",
        str(intro_audio)
    ], capture_output=True)
    
    # 片头视频：封面图 + 前3秒音频渐入
    subprocess.run([
        "ffmpeg", "-y",
        "-loop", "1", "-i", str(cover_path),
        "-i", str(intro_audio),
        "-c:v", "libx264", "-tune", "stillimage",
        "-preset", "medium", "-crf", "23",
        "-c:a", "aac", "-b:a", "192k",
        "-pix_fmt", "yuv420p",
        "-vf", "fade=t=in:st=0:d=1,colorbalance=rs=0.1:gs=0:bs=0",
        "-t", "3",
        "-movflags", "+faststart",
        str(intro_path)
    ], capture_output=True)
    
    # Step 3: 拼接片头 + 主视频（交叉淡入淡出）
    concat_file = output_path.parent / f"{output_path.stem}_concat.txt"
    with open(concat_file, 'w') as f:
        f.write(f"file '{intro_path.resolve()}'\n")
        f.write(f"file '{temp_main.resolve()}'\n")
    
    subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", str(concat_file),
        "-c", "copy",
        str(output_path)
    ], capture_output=True)
    
    result = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(output_path)],
        capture_output=True, text=True)
    final_dur = float(result.stdout.strip() or 0)
    
    size = os.path.getsize(str(output_path)) / (1024 * 1024)
    print(f"\n{'='*50}")
    print(f"  🌙 夜半低语 v4 生成完成! (含3秒片头)")
    print(f"  📁 {output_path.name} ({size:.1f}MB, {final_dur:.0f}s)")
    print(f"{'='*50}")

    # 清理临时文件
    for f in [temp_main, intro_path, intro_audio, concat_file]:
        try: f.unlink()
        except: pass


if __name__ == "__main__":
    asyncio.run(main())
