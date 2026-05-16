#!/usr/bin/env python3
"""
夜伴低语 v7 — 封面即背景 + 震撼BGM + 大字幕
====================================
改动亮点:
  - 封面即背景: 不再另做片头，封面直接作为整个视频的背景图
  - 大标题 + 系列名 "夜伴低语" 浮在画面上半部分
  - BGM音量大幅提升 (40%)，加入冲锋感频段
  - 字幕放大到 64px，Noto Sans CJK Black 粗体
  - 语音适度低沉 (音高下移8%)，保留清晰度
"""

import argparse
import asyncio
import math
import os
import random
import re
import subprocess
import struct
import textwrap
import wave
from pathlib import Path

# ─── 配置 ───────────────────────────────────────────────────
PROJECT_DIR = Path(__file__).resolve().parent.parent
STORIES_DIR  = PROJECT_DIR / "stories"
AUDIO_DIR    = PROJECT_DIR / "audio"
IMAGES_DIR   = PROJECT_DIR / "images"
VIDEOS_DIR   = PROJECT_DIR / "videos"
SCRIPTS_DIR  = Path(__file__).resolve().parent

# 字体路径
# 新增字体 — 主人下载的100font大礼包
FONT_PANGMEN_TTF = "/usr/share/fonts/100font/PangMenZhengDao-Regular.ttf"  # 庞门正道标题体（毛笔飞白）
FONT_SONG_HEAVY = "/usr/share/fonts/100font/SourceHanSerifCN-Heavy.otf"    # 思源宋体 Heavy
FONT_SONG_BOLD  = "/usr/share/fonts/100font/SourceHanSerifCN-Bold.otf"     # 思源宋体 Bold
FONT_ALIBABA_BLACK = "/usr/share/fonts/100font/AlibabaPuHuiTi-3-115-Black.otf"

FONT_BLACK   = "/usr/share/fonts/google-noto-cjk/NotoSansCJK-Black.ttc"
FONT_BOLD    = "/usr/share/fonts/google-noto-cjk/NotoSansCJK-Bold.ttc"
FONT_REGULAR = "/usr/share/fonts/google-noto-cjk/NotoSansCJK-Regular.ttc"
FONT_MICRO   = "/usr/share/fonts/wqy-microhei/wqy-microhei.ttc"

DEFAULT_VOICE  = "zh-CN-YunyangNeural"   # 成熟男声，更适合恐怖故事
WIDTH          = 1080
HEIGHT         = 1920
SUB_FONT_SIZE  = 54          # 手机版缩小字号，避免超出屏幕
TITLE_FONT_SIZE = 130        # 封面标题字号

# BGM 音量 (0~1)
BGM_VOLUME = 0.18             # 真实BGM音量18%

# FFmpeg 语音后处理参数
BASS_GAIN    = 4       # 低音增强4dB（不要太重）
REVERB_WET   = 0.6     # 混响湿声比例（加重）
ECHO_DELAY   = 0.08    # 回声延迟秒
ECHO_DECAY   = 0.30    # 回声衰减


def find_cn_font(prefer: str = "black") -> str:
    """返回可用字体"""
    candidates = {
        "black": FONT_BLACK,
        "bold": FONT_BOLD,
        "regular": FONT_REGULAR,
    }
    fp = candidates.get(prefer, FONT_BOLD)
    if os.path.exists(fp):
        return fp
    for f in [FONT_BLACK, FONT_BOLD, FONT_REGULAR, FONT_MICRO]:
        if os.path.exists(f):
            return f
    raise RuntimeError("找不到中文字体！")


def ensure_dirs():
    for d in [STORIES_DIR, AUDIO_DIR, IMAGES_DIR, VIDEOS_DIR]:
        d.mkdir(parents=True, exist_ok=True)


def clean_text(text: str, max_chars: int = 99999) -> str:
    """清洗故事文本（代码不再截断——字数控制由编剧铁律保障）
    
    规则：
    - 仅做基本清洗：去多余空格
    - 编剧保证≤1200字，保证3-4分钟全流程完成
    """
    text = re.sub(r'\s+', ' ', text).strip()
    if len(text) <= max_chars:
        return text
    
    # 智能缩写：保留开头 + 结尾高潮
    head_ratio = 0.35  # 开头占35%
    tail_ratio = 0.55  # 结尾占55%
    
    head_limit = int(max_chars * head_ratio)
    tail_limit = int(max_chars * tail_ratio)
    
    # 找到开头部分最后一个完整句
    head = text[:head_limit]
    head_cut = 0
    for punct in '。！？.!?\n':
        pos = head.rfind(punct)
        if pos > head_limit * 0.5:
            head_cut = pos + 1
            break
    if head_cut == 0:
        head_cut = head_limit
    
    # 找到结尾部分第一个完整句
    tail = text[-tail_limit:]
    tail_start = 0
    for punct in '。！？.!?\n':
        pos = tail.find(punct)
        if pos >= 0 and pos < tail_limit * 0.5:
            tail_start = pos + 1
            break
    
    # 组合
    result = text[:head_cut].rstrip() + "……" + text[-(tail_limit - tail_start):].lstrip()
    
    # 如果缩写后还是太长，再缩一次（保结尾）
    if len(result) > max_chars * 1.2:
        result = result[:int(max_chars * 0.4)] + "……" + result[-int(max_chars * 0.6):]
    
    print(f"  ✂️  故事过长({len(text)}字)，智能缩写为{len(result)}字")
    return result


# ═══════════════════════════════════════════════════════════════
#  标签驱动情感音频后处理（轻量版 v2）
#  编剧标注 → FFmpeg分段渲染 → acrossfade平滑拼接 → 音量归一
# ═══════════════════════════════════════════════════════════════

# 语气 → FFmpeg效果映射
# 原则：只改音高+EQ，不加echo/混响，保持语音清晰
TONE_EFFECTS = {
    '平静': {'filter': 'volume=1.0', 'desc': '原声'},
    '恐惧': {'filter': 'asetrate=45423,aresample=44100,atempo=0.971', 'desc': '音高+3%'},         # 音高微升，紧张感
    '愤怒': {'filter': 'asetrate=41900,aresample=44100,atempo=1.053,equalizer=f=200:t=q:w=1:g=4', 'desc': '音高-5%+中低频'},  # 音高略降，增低频
    '悲伤': {'filter': 'atempo=0.96,equalizer=f=3000:t=q:w=1:g=-4', 'desc': '减速4%+降高频'},     # 略慢，高频滚降
    '轻声': {'filter': 'volume=0.7,equalizer=f=4000:t=q:w=1:g=3', 'desc': '音量70%+高频提升'},    # 小声，增加气息感
    '尖锐': {'filter': 'asetrate=46305,aresample=44100,atempo=0.953,equalizer=f=5000:t=q:w=1:g=3', 'desc': '音高+5%+高频'},
}


def parse_scribe_tags(story_text: str) -> list:
    """解析编剧标注格式 [语气｜配乐｜画面] 文本→段落列表"""
    import re
    lines = story_text.strip().split('\n')
    segments = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        # 匹配 [语气｜配乐｜画面] 正文
        m = re.match(r'\[([^\]]+)\]', line)
        if m:
            tags = m.group(1).split('｜')
            tone = tags[0].strip() if len(tags) > 0 else '平静'
            music = tags[1].strip() if len(tags) > 1 else '安静'
            scene = '|'.join(tags[2:]).strip() if len(tags) > 2 else ''
            text = line[m.end():].strip()
            # 去引号
            text = re.sub(r'^["\'""]|["\'""]$', '', text).strip()
            if text:
                segments.append({'tone': tone, 'music': music, 'scene': scene, 'text': text})
        else:
            # 无标签的行（fallback）
            text = re.sub(r'^["\'""]|["\'""]$', '', line).strip()
            if text:
                segments.append({'tone': '平静', 'music': '安静', 'scene': '', 'text': text})
    return segments


def apply_tone_processing(audio_path: Path, segments_with_timing: list,
                           output_path: Path) -> Path:
    """按段落的语气标签，逐段渲染不同音高+EQ效果
    
    - atrim 提取每段 → 按tone加滤镜 → acrossfade平滑拼接
    - 最后 dynaudnorm 统一全场音量
    - 效采够轻，不破坏语音清晰度
    """
    total_segs = len(segments_with_timing)
    if total_segs == 0:
        return audio_path
    
    # 合并相邻相同语气，减少滤镜复杂度
    merged = []
    for seg in segments_with_timing:
        if merged and merged[-1]['tone'] == seg['tone']:
            merged[-1]['end'] = seg['end']
            merged[-1]['text'] += seg.get('text', '')
        else:
            merged.append({**seg})
    
    # 构建filter chain
    filter_parts = []
    seg_labels = []
    crossfade_dur = 0.15  # 短交叉淡化，平滑过渡
    
    for i, seg in enumerate(merged):
        start = seg['start']
        dur = seg['end'] - start
        tone = seg.get('tone', '平静')
        effect = TONE_EFFECTS.get(tone, TONE_EFFECTS['平静'])
        label = f"t{i}"
        
        # atrim提取 + 效果滤镜
        atrim_expr = f"start={start:.2f}:duration={dur:.2f}"
        filter_parts.append(
            f"[0:a]atrim={atrim_expr},{effect['filter']}[{label}]"
        )
        seg_labels.append(label)
    
    # 用acrossfade链式拼接（比concat平滑）
    if len(seg_labels) == 1:
        # 一段直接输出
        filter_chain = ";".join(filter_parts)
        cmd = ["ffmpeg", "-y", "-i", str(audio_path),
               "-filter_complex", filter_chain,
               "-map", f"[{seg_labels[0]}]",
               "-acodec", "pcm_s16le",
               str(output_path)]
    else:
        # 多段：链式acrossfade
        current_label = seg_labels[0]
        for i in range(1, len(seg_labels)):
            next_label = seg_labels[i]
            tmp_label = f"f{i}" if i < len(seg_labels) - 1 else "out"
            acrossfade = (
                f"[{current_label}][{next_label}]"
                f"acrossfade=d={crossfade_dur}:c1=tri:c2=tri[{tmp_label}]"
            )
            filter_parts.append(acrossfade)
            current_label = tmp_label
        
        # 最后dynaudnorm统一音量（避免忽大忽小）
        filter_parts.append(f"[out]dynaudnorm=p=0.9:m=10[final]")
        filter_chain = ";".join(filter_parts)
        
        cmd = ["ffmpeg", "-y", "-i", str(audio_path),
               "-filter_complex", filter_chain,
               "-map", "[final]",
               "-acodec", "pcm_s16le",
               str(output_path)]
    
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        print(f"  ⚠️  语气处理失败，回退原声: {result.stderr[-200:]}")
        return audio_path
    
    # 统计各语气
    tone_counts = {}
    for seg in segments_with_timing:
        t = seg.get('tone', '平静')
        tone_counts[t] = tone_counts.get(t, 0) + 1
    summary = " | ".join(f"{k}:{v}" for k, v in sorted(tone_counts.items()))
    print(f"  🎭 语气渲染: {summary}")
    return output_path


def split_into_segments(text: str, max_len: int = 20) -> list:
    """
    将文本分成字幕段，每段不超过 max_len 字符
    智能处理标点，不会被单独截断
    """
    # 先用句末标点分句
    sentences = []
    buffer = ""
    for char in text:
        buffer += char
        if char in '。！？.!?' and len(buffer) >= 3:
            sentences.append(buffer.strip())
            buffer = ""
    if buffer.strip():
        sentences.append(buffer.strip())
    if not sentences:
        sentences = [text]

    # 对每句控制长度
    result = []
    for s in sentences:
        s = s.strip()
        if not s:
            continue
        # 如果只有标点符号，合并到上一段
        if len(s) <= 1 and s in '。！？.!?' and result:
            result[-1] += s
            continue
        if len(s) <= max_len:
            result.append(s)
        else:
            # 长句按最大长度截断，但尽量在词中间断开
            parts = []
            remaining = s
            while remaining:
                # 取前max_len个字符
                part = remaining[:max_len]
                if len(remaining) <= max_len:
                    parts.append(remaining)
                    break
                # 如果在截断位置附近有逗号/空格，在那里断开更自然
                cut_pos = max_len
                for punct in reversed(',，、；;'):
                    pos = part.rfind(punct)
                    if pos > max_len * 0.5:
                        cut_pos = pos + 1
                        break
                parts.append(remaining[:cut_pos])
                remaining = remaining[cut_pos:]
            result.extend(parts)

    # 过滤纯标点段
    result = [seg for seg in result if seg.strip() and not all(c in '。！？，、；：""'' ' for c in seg.strip())]
    return result if result else [text]
async def generate_audio(text: str, voice: str, output_path: Path) -> float:
    """生成配音音频"""
    import edge_tts
    print(f"  🎙️  配音中... {voice}")
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(str(output_path))

    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(output_path)],
        capture_output=True, text=True
    )
    duration = float(result.stdout.strip() or 0)
    print(f"      时长: {duration:.1f}s")
    return duration


# ── 情感分段配音（基于edge-tts原生rate/pitch参数）──
# 由  的 [语气｜配乐｜画面] 标签驱动
# 情绪预设参考: EdgeTTS-Studio (sunnyvucs/EdgeTTS-Studio)

TONE_TO_PARAMS = {
    '平静':   {'rate': '-15%',  'pitch': '-3Hz'},
    '恐惧':   {'rate': '-5%',   'pitch': '+5Hz'},
    '愤怒':   {'rate': '+20%',  'pitch': '+8Hz'},
    '悲伤':   {'rate': '-20%',  'pitch': '-5Hz'},
    '轻声':   {'rate': '-10%',  'pitch': '+0Hz', 'vol_boost': 1.5},
    '尖锐':   {'rate': '+10%',  'pitch': '+10Hz'},
}

async def generate_emotional_audio(tagged_segments: list, voice: str,
                                    output_path: Path) -> float:
    """按编剧标注的语气标签，分段生成带情绪的TTS配音
    
    每段调用 edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
    最后用FFmpeg concat拼接成完整音频。
    情绪直接打在TTS生成层（rate/pitch），而非后处理。
    """
    import edge_tts
    import random as rnd
    
    # 合并相邻相同语气的段（减少TTS调用次数+拼接更顺滑）
    merged = []
    for seg in tagged_segments:
        if merged and merged[-1]['tone'] == seg['tone']:
            merged[-1]['text'] += '。' + seg['text']
        else:
            merged.append({'tone': seg['tone'], 'text': seg['text']})
    
    total_segs = len(merged)
    print(f"  🎙️  分词生成({voice}, {total_segs}段)...")
    
    # 为每段生成TTS
    temp_dir = output_path.parent / f".segments_{rnd.randint(10000,99999)}"
    temp_dir.mkdir(exist_ok=True)
    
    temp_files = []
    segment_texts = []
    
    for i, seg in enumerate(merged):
        tone = seg['tone']
        text = seg['text']
        params = TONE_TO_PARAMS.get(tone, TONE_TO_PARAMS['平静'])
        
        temp_path = temp_dir / f"seg_{i:03d}.mp3"
        
        try:
            communicate = edge_tts.Communicate(
                text, voice,
                rate=params['rate'],
                pitch=params['pitch']
            )
            await communicate.save(str(temp_path))
            
            # 静音段（轻声效果需要降低音量，加一个volume滤镜）
            if tone == '轻声':
                vol_path = temp_dir / f"seg_{i:03d}_quiet.mp3"
                subprocess.run([
                    "ffmpeg", "-y", "-i", str(temp_path),
                    "-af", f"volume={params.get('vol_boost', 1)}",
                    "-acodec", "libmp3lame",
                    str(vol_path)
                ], capture_output=True, timeout=30)
                temp_files.append(vol_path)
            else:
                temp_files.append(temp_path)
            
            segment_texts.append(text)
            
            # 小量信息
            tone_mark = {"平静":"·","恐惧":"😨","愤怒":"😠","悲伤":"😢","轻声":"🤫","尖锐":"🗡️"}.get(tone, "·")
            print(f"    [{i+1:02d}/{total_segs}] {tone_mark}{tone} ({params['rate']}, {params['pitch']}) {text[:25]}...")
            
        except Exception as e:
            print(f"    ⚠️  段{i}生成失败({tone}): {e}")
            return 0.0
    
    # 用FFmpeg concat拼接所有段
    concat_file = temp_dir / "concat_list.txt"
    concat_content = "\n".join(f"file '{f.name}'" for f in temp_files)
    concat_file.write_text(concat_content)
    
    # 用concat demuxer拼接（无需重新编码，保留MP3质量）
    result = subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", str(concat_file),
        "-c", "copy",
        str(output_path)
    ], capture_output=True, text=True, timeout=120)
    
    if result.returncode != 0:
        print(f"  ⚠️  音频拼接失败: {result.stderr[-200:]}")
        # 回退：直接用第一段
        import shutil
        shutil.copy(temp_files[0], output_path)
    
    # 清理临时文件
    import shutil
    try:
        shutil.rmtree(str(temp_dir))
    except:
        pass
    
    # 获取总时长
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(output_path)],
        capture_output=True, text=True
    )
    duration = float(probe.stdout.strip() or 0)
    
    # 统计
    tone_counts = {}
    for seg in tagged_segments:
        t = seg['tone']
        tone_counts[t] = tone_counts.get(t, 0) + 1
    summary = " | ".join(f"{k}:{v}" for k, v in sorted(tone_counts.items()))
    print(f"      总时长: {duration:.1f}s | 语气: {summary}")
    
    return duration


def apply_voice_processing(input_path: Path, output_path: Path):
    """
    语音后处理: 音高下移 + Bass增强 + 回声
    使用FFmpeg的rubberband实现高质量音高变化
    """
    print(f"  🔊 语音后处理...")
    cmd = [
        "ffmpeg", "-y",
        "-i", str(input_path),
        "-af",
        "volume=5.0,alimiter=limit=0.9,"  # 放大5倍+限幅防失真
        f"equalizer=f=80:t=q:w=1.5:g={BASS_GAIN},"
        f"equalizer=f=3000:t=q:w=1:g=6,"    # 增强3kHz人声清晰度
        f"aecho={ECHO_DELAY}:{ECHO_DECAY}:1:0.5,"
        f"apad=pad_dur=1.5",
        "-acodec", "pcm_s16le",
        str(output_path)
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  ⚠️  语音处理失败: {result.stderr[-200:]}")
        print(f"      回退到原声")
        return str(input_path)
    print(f"      低音+{BASS_GAIN}dB, 回声+混响 ✓")
    return str(output_path)


# ═══════════════════════════════════════════════════════════════
#  BGM — 增强版恐怖配乐
# ═══════════════════════════════════════════════════════════════

SAMPLE_RATE = 22050
BASE_FREQ = 110  # A2


def note_to_freq(semitones: int) -> float:
    return BASE_FREQ * (2 ** (semitones / 12))


def generate_bass_drone(duration: float, sr=SAMPLE_RATE) -> list:
    """低音嗡鸣 — 加强版，更低更厚"""
    n = int(sr * duration)
    result = [0.0] * n
    freqs = [28, 35, 42]  # 三个超低频叠加
    for t in range(n):
        env = min(1.0, t / (sr * 0.8), (n - t) / (sr * 1.0))
        val = 0.0
        for f in freqs:
            val += math.sin(2 * math.pi * f * t / sr)
            val += 0.2 * math.sin(2 * math.pi * (f / 2) * t / sr)  # 次谐波
        result[t] += val / len(freqs) * 0.35 * env
    return result


def generate_horror_piano(duration: float, sr=SAMPLE_RATE, density=0.35) -> list:
    """恐怖钢琴 — 更密集，更强"""
    n = int(sr * duration)
    result = [0.0] * n
    rng = random.Random(42)

    current_time = 0
    while current_time < duration:
        semitones = rng.choice([0, 3, 5, 6, 7, 10, 13, 15, 17, 18, 22])
        freq = note_to_freq(semitones + rng.choice([0, 12, 24, -12]))
        note_dur = rng.uniform(0.4, 1.8)
        note_start = int(current_time * sr)
        note_end = min(n, int((current_time + note_dur) * sr))

        for i in range(note_start, note_end):
            pos = i
            if pos >= n:
                break
            env = math.exp(-(pos - note_start) / (sr * 0.25))
            if env < 0.01:
                break
            fundamental = math.sin(2 * math.pi * freq * (pos - note_start) / sr)
            overtone1 = 0.3 * math.sin(2 * math.pi * freq * 2 * (pos - note_start) / sr)
            overtone2 = 0.1 * math.sin(2 * math.pi * freq * 3 * (pos - note_start) / sr)
            result[pos] += 0.18 * env * (fundamental + overtone1 + overtone2) * 0.7

        gap = rng.uniform(1.0, 2.0)
        current_time += note_dur + gap
    return result


def generate_string_pad(duration: float, sr=SAMPLE_RATE) -> list:
    """弦乐垫 — 加强版"""
    n = int(sr * duration)
    result = [0.0] * n
    rng = random.Random(43)

    chords = [
        [0, 3, 7],     # Am
        [5, 8, 12],    # Dm
        [7, 10, 14],   # Em
        [8, 12, 15],   # F
        [3, 6, 10],    # Cdim
    ]

    current_time = 0
    while current_time < duration:
        chord = rng.choice(chords)
        chord_dur = rng.uniform(3, 7)
        chord_end = min(duration, current_time + chord_dur)
        cs = int(current_time * sr)
        ce = int(chord_end * sr)

        for semi in chord:
            freq = note_to_freq(semi - 12)
            freq2 = note_to_freq(semi)
            for i in range(cs, ce):
                if i >= n:
                    break
                t = (i - cs) / sr
                progress = (i - cs) / max(1, ce - cs)
                amp_mod = 0.7 + 0.3 * math.sin(2 * math.pi * 0.12 * t)
                fade = min(1.0, progress * 3, (1 - progress) * 3)
                saw = 2 * (freq * t - math.floor(freq * t + 0.5))
                tone = (0.4 * math.sin(2 * math.pi * freq * t) +
                       0.4 * saw +
                       0.2 * math.sin(2 * math.pi * freq2 * t))
                result[i] += 0.06 * amp_mod * fade * tone
        current_time += chord_dur
    return result


def generate_impact_sweeps(duration: float, sr=SAMPLE_RATE) -> list:
    """
    冲击感扫频 — 新增！模拟恐怖片中的"冲击波"效果
    升高或降低的扫频带来紧张感
    """
    n = int(sr * duration)
    result = [0.0] * n
    rng = random.Random(46)

    num_sweeps = rng.randint(3, 6)
    for _ in range(num_sweeps):
        start = rng.randint(int(sr * 2), n - int(sr * 3))
        sweep_dur = rng.uniform(0.6, 1.5)
        end_pos = min(n, start + int(sweep_dur * sr))
        f_start = rng.uniform(40, 120)
        f_end = rng.uniform(300, 1200)
        rise = rng.choice([True, False])
        if not rise:
            f_start, f_end = f_end, f_start

        for i in range(start, end_pos):
            if i >= n:
                break
            t = (i - start) / (end_pos - start)
            env = math.sin(math.pi * t)  # 渐强渐弱
            # 线性变化频率
            freq = f_start + (f_end - f_start) * t
            sample = math.sin(2 * math.pi * freq * (i - start) / sr)
            sample += 0.5 * math.sin(2 * math.pi * freq * 1.5 * (i - start) / sr)
            result[i] += 0.07 * env * sample

    return result


def generate_atonal_swell(duration: float, sr=SAMPLE_RATE) -> list:
    """不和谐音簇 — 加强版"""
    n = int(sr * duration)
    result = [0.0] * n
    rng = random.Random(44)

    num_swells = rng.randint(2, 4)
    for _ in range(num_swells):
        start = rng.randint(int(sr * 3), n - int(sr * 2))
        swell_dur = rng.uniform(1.0, 2.5)
        swell_end = min(n, start + int(swell_dur * sr))
        freqs = [rng.uniform(200, 1000) for _ in range(rng.randint(4, 7))]

        for i in range(start, swell_end):
            t = (i - start) / (swell_end - start)
            env = math.sin(math.pi * t)
            sample = sum(math.sin(2 * math.pi * f * (i - start) / sr)
                        for f in freqs) / len(freqs)
            result[i] += 0.08 * env * sample
    return result


def generate_wind_noise(duration: float, sr=SAMPLE_RATE) -> list:
    """风噪声 — 更明显"""
    n = int(sr * duration)
    rng = random.Random(45)
    result = [0.0] * n
    for t in range(0, n, sr // 20):
        chunk_end = min(t + sr // 20, n)
        wind_var = 0.5 + 0.5 * math.sin(2 * math.pi * 0.03 * t / sr)
        amp = 0.02 + 0.04 * wind_var
        for i in range(t, chunk_end):
            result[i] += rng.uniform(-1, 1) * amp
    return result


def generate_heartbeat(duration: float, bpm=68, sr=SAMPLE_RATE) -> list:
    """心跳 — 加强，加BPM随进度加快"""
    n = int(sr * duration)
    result = [0.0] * n
    beat_interval_base = int(60.0 / bpm * sr)
    lub_len = int(0.08 * sr)
    dub_offset = int(0.14 * sr)
    dub_len = int(0.06 * sr)

    for beat_num, beat_start in enumerate(range(int(sr * 1.5), n, beat_interval_base)):
        # BPM逐渐加快 (恐怖片经典手法)
        progress = beat_start / n
        speed_up = 1.0 - progress * 0.3  # 最快加快30%
        actual_interval = int(beat_interval_base * speed_up)
        if beat_num > 0:
            actual_start = int(sr * 1.5) + beat_num * actual_interval
        else:
            actual_start = beat_start
            continue

        # lub
        for i in range(lub_len):
            pos = actual_start + i
            if pos < n:
                env = math.sin(math.pi * i / lub_len)
                result[pos] += 0.15 * env * math.sin(2 * math.pi * 60 * i / sr)
        # dub
        for i in range(dub_len):
            pos = actual_start + dub_offset + i
            if pos < n:
                env = math.sin(math.pi * i / dub_len)
                result[pos] += 0.10 * env * math.sin(2 * math.pi * 75 * i / sr)
    return result


def generate_bgm_full(duration: float, sr=SAMPLE_RATE,
                      include_heartbeat=False) -> list:
    """v7增强版恐怖配乐"""
    n = int(sr * duration)
    print(f"  🎵 合成增强版恐怖配乐 v7...")
    print(f"      时长={duration:.1f}s{' +心跳' if include_heartbeat else ''}")

    layers = {
        'bass': generate_bass_drone(duration, sr),
        'wind': generate_wind_noise(duration, sr),
        'piano': generate_horror_piano(duration, sr),
        'strings': generate_string_pad(duration, sr),
        'swells': generate_atonal_swell(duration, sr),
        'impacts': generate_impact_sweeps(duration, sr),
    }
    for name in layers:
        print(f"      {name} ✅")

    if include_heartbeat:
        layers['heart'] = generate_heartbeat(duration, sr)
        print(f"      heartbeat ✅")

    # 混合
    result = [0.0] * n
    for samples in layers.values():
        for i in range(min(n, len(samples))):
            result[i] += samples[i]

    # 温和归一化 (保留动态范围)
    max_val = max(abs(s) for s in result) or 1.0
    if max_val > 0.8:
        result = [s * 0.8 / max_val for s in result]

    return result


def save_wav(samples: list, output_path: Path, sr=SAMPLE_RATE):
    n_samples = len(samples)
    with wave.open(str(output_path), 'w') as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sr)
        for s in samples:
            int_val = int(max(-32768, min(32767, s * 32767)))
            wav.writeframes(struct.pack('<h', int_val))
    size = os.path.getsize(str(output_path)) / 1024
    print(f"  ✅ BGM保存: {output_path.name} ({size:.0f}KB)")


def generate_bgm(duration, output_path, heartbeat=False):
    samples = generate_bgm_full(duration + 1, include_heartbeat=heartbeat)
    save_wav(samples, output_path)


# ═══════════════════════════════════════════════════════════════
#  封面背景生成 — 封面即背景
# ═══════════════════════════════════════════════════════════════

def create_story_background_with_title(
    output_path: Path,
    story_title: str = "镜中人",
    series_name: str = "夜伴低语",
    width: int = WIDTH,
    height: int = HEIGHT,
    seed: int = None
):
    """
    生成张震风格封面即背景
    ──────────────────────
    设计参考: 张震讲鬼故事封面
    - 纯黑 + 颗粒噪点做旧（非渐变）
    - 竖排血红大字 + 白色手绘边框
    - 极简三色: 黑 + 血红 + 白
    """
    from PIL import Image, ImageDraw, ImageFilter, ImageFont

    rng = random.Random(seed or 42)
    print(f"  🎨 生成张震风格封面即背景...")

    img = Image.new("RGB", (width, height), color=(0, 0, 0))
    draw = ImageDraw.Draw(img)

    # ─── 1. 纯黑 + 噪点颗粒纹理 ────────────────
    # 在纯黑底上均匀撒噪点（模拟老式胶片/宣纸做旧）
    noise = Image.new("RGB", (width, height), color=(0, 0, 0))
    noise_draw = ImageDraw.Draw(noise)
    for _ in range(50000):
        x = rng.randint(0, width - 1)
        y = rng.randint(0, height - 1)
        v = rng.randint(0, max(1, int(12)))
        noise_draw.point((x, y), fill=(v, v, v))
    noise = noise.filter(ImageFilter.GaussianBlur(radius=2))
    img = Image.blend(img, noise, 0.6)

    # ─── 2. 轻微做旧污渍（烟熏效果） ──────────
    stain = Image.new("RGB", (width, height), color=(0, 0, 0))
    stain_draw = ImageDraw.Draw(stain)
    for _ in range(20):
        sx = rng.randint(0, width)
        sy = rng.randint(0, height)
        sr_ = rng.randint(100, 400)
        v = rng.randint(2, 6)
        stain_draw.ellipse([sx-sr_, sy-sr_, sx+sr_, sy+sr_], fill=(v, v, v))
    stain = stain.filter(ImageFilter.GaussianBlur(radius=60))
    img = Image.blend(img, stain, 0.4)

    # ─── 3. 暗角强化 ────────────────────────────
    cx, cy = width // 2, height // 2
    max_radius = int(math.sqrt(cx**2 + cy**2))
    vignette = Image.new("RGB", (width, height), color=(0, 0, 0))
    v_draw = ImageDraw.Draw(vignette)
    for r in range(int(max_radius * 1.5), int(max_radius * 0.3), -1):
        t = (r - max_radius * 0.3) / (max_radius * 1.2)
        if t < 0:
            continue
        alpha = int(200 * min(1.0, t * 0.9))
        v_draw.ellipse([cx - r, cy - r*1.3, cx + r, cy + r*1.3],
                       fill=(alpha, alpha, alpha))
    vignette = vignette.filter(ImageFilter.GaussianBlur(radius=40))
    # 改用像素操作制作暗角遮罩
    v_data = list(vignette.getdata())
    max_v = max(max(rgb) for rgb in v_data) or 255
    mask_data = [int(255 - max(rgb) * 0.5 / max_v * 255) for rgb in v_data]
    mask_img = Image.new('L', (width, height))
    mask_img.putdata(mask_data)
    img = Image.composite(img, Image.new("RGB", (width, height), color=(0, 0, 0)), mask_img)

    # ─── 4. 竖排大字（参考图风格：单列竖排） ────
    # 四个字竖排一列: 夜 → 半 → 低 → 语
    # 参考可灵AI的"夜伴低语"封面设计

    try:
        font_char = ImageFont.truetype(FONT_PANGMEN_TTF, 250)  # 大字用庞门正道（毛笔飞白）
        font_sub = ImageFont.truetype(FONT_PANGMEN_TTF, 52)     # 小字
        font_series_name = ImageFont.truetype(FONT_PANGMEN_TTF, 60)  # 系列名
    except Exception:
        try:
            font_char = ImageFont.truetype(FONT_BLACK, 250)
            font_sub = ImageFont.truetype(FONT_BLACK, 52)
            font_series_name = ImageFont.truetype(FONT_BLACK, 60)
        except:
            font_char = ImageFont.truetype(find_cn_font("bold"), 250)
            font_sub = ImageFont.truetype(find_cn_font("bold"), 52)
            font_series_name = ImageFont.truetype(find_cn_font("bold"), 60)

    draw2 = ImageDraw.Draw(img)

    # 配色
    BLOOD_RED = (179, 0, 0)        # #B30000 血色主字
    WHITE     = (255, 255, 255)
    LIGHT_GRAY = (180, 180, 180)

    # 四个字竖排一列: 夜 半 低 语
    chars = ["夜", "半", "低", "语"]

    # 计算每个字的尺寸，找出最大的
    char_bboxes = []
    for ch in chars:
        bbox = draw2.textbbox((0, 0), ch, font=font_char)
        cw = bbox[2] - bbox[0]
        ch_h = bbox[3] - bbox[1]
        char_bboxes.append((cw, ch_h))

    max_cw = max(b[0] for b in char_bboxes)
    char_spacing = 260  # 上下间距

    # 整体居中（上移至视觉中心）
    total_height = sum(b[1] for b in char_bboxes) + char_spacing * 3
    start_y = (1920 - total_height) // 2 - 80  # 整体上移留字幕位

    # ─── 绘制四个大字 ─────────────────────────
    for i, ch in enumerate(chars):
        cw, ch_h = char_bboxes[i]
        x = (1080 - cw) // 2
        y = start_y + i * (ch_h + char_spacing)

        # 随机手写偏移
        ox = rng.randint(-2, 2)
        oy = rng.randint(-2, 2)

        # 多重黑色阴影描边（参考图风格：厚重描边）
        for dx2, dy2 in [(-8, -8), (-8, 8), (8, -8), (8, 8),
                         (-10, 0), (10, 0), (0, -10), (0, 10),
                         (-5, -5), (-5, 5), (5, -5), (5, 5),
                         (-12, -4), (-12, 4), (12, -4), (12, 4),
                         (-4, -12), (-4, 12), (4, -12), (4, 12)]:
            draw2.text((x + dx2 + ox, y + dy2 + oy),
                      ch, font=font_char, fill=(0, 0, 0, 220))

        # 主字（血红色）
        draw2.text((x + ox, y + oy),
                  ch, font=font_char, fill=BLOOD_RED)

    # ─── 5. 顶部系列名 ─────────────────────────
    series_text = "— 夜伴低语 —"
    bbox_s = draw2.textbbox((0, 0), series_text, font=font_series_name)
    sw = bbox_s[2] - bbox_s[0]
    draw2.text(((1080 - sw) // 2, 120), series_text,
               font=font_series_name, fill=LIGHT_GRAY)

    # ─── 6. 底部故事名 ─────────────────────────
    story_sub = f"— {story_title} —"
    bbox_st = draw2.textbbox((0, 0), story_sub, font=font_sub)
    stw = bbox_st[2] - bbox_st[0]
    draw2.text(((1080 - stw) // 2, 1920 - 250), story_sub,
               font=font_sub, fill=LIGHT_GRAY)

    # ─── 6. 白色手绘边框 ──────────────────────
    # 模仿张震的白色撕裂边框（白色手绘线，有断点毛刺）
    border_margin = 60
    b_x1 = border_margin
    b_y1 = border_margin
    b_x2 = width - border_margin
    b_y2 = height - border_margin

    # 上边框
    for step in range(0, b_x2 - b_x1, 4):
        jitter = rng.randint(-3, 3)
        thickness = rng.randint(2, 4)
        x = b_x1 + step
        y = b_y1 + jitter
        draw2.rectangle([x, y, x + thickness, y + thickness],
                        fill=(255, 255, 255, 180))
    # 下边框
    for step in range(0, b_x2 - b_x1, 4):
        jitter = rng.randint(-3, 3)
        thickness = rng.randint(2, 4)
        x = b_x1 + step
        y = b_y2 + jitter
        draw2.rectangle([x, y - thickness, x + thickness, y],
                        fill=(255, 255, 255, 180))
    # 左边框
    for step in range(0, b_y2 - b_y1, 4):
        jitter = rng.randint(-3, 3)
        thickness = rng.randint(2, 4)
        x = b_x1 + jitter
        y = b_y1 + step
        draw2.rectangle([x, y, x + thickness, y + thickness],
                        fill=(255, 255, 255, 180))
    # 右边框
    for step in range(0, b_y2 - b_y1, 4):
        jitter = rng.randint(-3, 3)
        thickness = rng.randint(2, 4)
        x = b_x2 + jitter
        y = b_y1 + step
        draw2.rectangle([x - thickness, y, x, y + thickness],
                        fill=(255, 255, 255, 180))

    # 边框四角加点中断效果（随机缺失几段）
    for _ in range(rng.randint(4, 8)):
        corner = rng.choice(['tl', 'tr', 'bl', 'br'])
        cx_ = {'tl': b_x1, 'tr': b_x2, 'bl': b_x1, 'br': b_x2}[corner]
        cy_ = {'tl': b_y1, 'tr': b_y1, 'bl': b_y2, 'br': b_y2}[corner]
        size = rng.randint(8, 25)
        # 在角上画黑色方块"擦除"一段边框
        draw2.rectangle([cx_ - 5, cy_ - 5, cx_ + size, cy_ + size],
                        fill=(0, 0, 0))

    # ─── 7. 保存 ────────────────────────────────
    img.save(str(output_path), quality=95)
    print(f"      张震风格封面 → {output_path.name}")
    return str(output_path)


# ═══════════════════════════════════════════════════════════════
#  BGM拼接 + 视频合成
# ═══════════════════════════════════════════════════════════════

def combine_bgm_files(bgm_file_list: list, target_duration: float, output_dir: Path, select_count: int = 3) -> Path:
    """多BGM交叉淡入淡出拼接，匹配目标时长
    
    随机选 select_count 首BGM，用FFmpeg acrossfade拼接，
    确保总时长 ≥ target_duration，返回拼接后的wav路径。
    """
    import random as rnd
    rnd.seed(42)  # 固定种子保证同一故事每次选同一组BGM
    
    n_available = len(bgm_file_list)
    n_pick = min(select_count, n_available)
    selected = rnd.sample(bgm_file_list, n_pick)
    
    # 检测每个BGM时长，不够就多加
    def get_dur(path):
        probe = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
            capture_output=True, text=True
        )
        return float(probe.stdout.strip() or 30)
    
    bgms = [(Path(f), get_dur(f)) for f in selected]
    total_dur = sum(d for _, d in bgms)
    
    # 总时长不够目标，从剩余文件里继续加（确保内容覆盖全程）
    remaining = [Path(f) for f in bgm_file_list if f not in [str(x[0]) for x in bgms]]
    while total_dur < target_duration and remaining:
        f = rnd.choice(remaining)
        remaining.remove(f)
        d = get_dur(f)
        bgms.append((f, d))
        total_dur += d
    
    # 拼FFmpeg命令
    crossfade = 2  # 2秒交叉淡入淡出
    input_args = []
    for f, _ in bgms:
        input_args.extend(["-i", str(f)])
    
    # 构建filter chain:
    #  [0:a]atrim=d=d0[bgm0];[bgm0][1:a]acrossfade[tmp0];...[tmpN-2][N-1:a]acrossfade[out]
    if len(bgms) == 1:
        filter_str = f"[0:a]atrim=duration={target_duration + 1}[out]"
    else:
        parts = [f"[0:a]atrim=duration={bgms[0][1]}[bgm0]"]
        for i in range(1, len(bgms)):
            prev = "bgm0" if i == 1 else f"tmp{i-2}"
            out_label = f"tmp{i-1}" if i < len(bgms) - 1 else "out"
            parts.append(
                f"[{prev}][{i}:a]acrossfade=d={crossfade}:c1=tri:c2=tri[{out_label}]"
            )
        filter_str = ";".join(parts)
    
    output = output_dir / f"combined_bgm_{abs(hash(str(bgms))) % 100000}.wav"
    cmd = ["ffmpeg", "-y"] + input_args + [
        "-filter_complex", filter_str,
        "-map", "[out]",
        "-t", str(target_duration + 0.5),
        "-acodec", "pcm_s16le",
        "-vn",
        str(output)
    ]
    subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    
    # 验证输出文件
    if not output.exists() or output.stat().st_size == 0:
        print(f"  ⚠️  BGM拼接失败，文件为空，回退到单曲模式")
        # 回退：直接用第一首BGM
        fallback = Path(bgm_file_list[0])
        return fallback
    
    # 检测拼接后的实际时长
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(output)],
        capture_output=True, text=True
    )
    actual_dur = float(probe.stdout.strip() or 0)
    
    names = " + ".join(f.stem[:15] for f, _ in bgms)
    print(f"      BGM多曲拼接: {names}")
    print(f"      BGM总时长: {actual_dur:.0f}s, picks: {len(bgms)}首")
    return output


def assemble_video_v7(audio_path: Path, bg_image_path: Path,
                       story_segments: list, output_path: Path,
                       total_duration: float, story_title: str = "",
                       bgm_path: Path = None,
                       heartbeat: bool = False,
                       scene_images: list = None,
                       cover_path: Path = None) -> bool:
    """
    v7视频合成: 封面片头 + 场景图切换 + 大字幕 + 震撼BGM
    
    参数:
      scene_images: 可选，每段对应的场景图片列表（长度与story_segments相同）
                    提供后按段切换背景图，不提供则用单张bg_image_path
      cover_path:   可选，夜伴低语封面图，提供后作为视频第一帧（约3秒）
    """
    COVER_DURATION = 3.0  # 封面展示时长（秒）
    print(f"\n  🎬 合成 v7 视频...")
    font_path = find_cn_font("black")  # 用Black粗体
    print(f"      字体: {font_path} (Noto Sans CJK Black)")

    # ─── BGM混音 (音量提升到40%) ──────────────────
    # ─── BGM混音 + 循环补齐 ──────────────────────
    if bgm_path and bgm_path.exists():
        print(f"      BGM: {bgm_path.name} (音量{BGM_VOLUME*100:.0f}%)")
        
        # 检测BGM时长
        probe = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(bgm_path)],
            capture_output=True, text=True
        )
        bgm_dur = float(probe.stdout.strip() or 0)
        
        # 如果BGM不够长，循环到追上配音时长
        need_loop = bgm_dur < total_duration * 0.8
        if need_loop:
            loops_needed = int(total_duration / bgm_dur) + 2
            looped_bgm = output_path.parent / f"{output_path.stem}_looped_bgm.wav"
            loop_cmd = [
                "ffmpeg", "-y",
                "-stream_loop", str(loops_needed),
                "-i", str(bgm_path),
                "-t", str(total_duration + 0.5),
                "-acodec", "pcm_s16le",
                str(looped_bgm)
            ]
            subprocess.run(loop_cmd, capture_output=True, text=True)
            bgm_source = str(looped_bgm)
            print(f"      BGM循环补齐: {bgm_dur:.0f}s × {loops_needed} ≈ {bgm_dur*loops_needed:.0f}s ✓")
        else:
            bgm_source = str(bgm_path)
        
        mixed_audio = output_path.parent / f"{output_path.stem}_mixed_audio.wav"
        mix_cmd = [
            "ffmpeg", "-y",
            "-i", str(audio_path),
            "-i", bgm_source,
            "-filter_complex",
            f"[1:a]volume={BGM_VOLUME}[bgm];"
            f"[0:a][bgm]amix=inputs=2:duration=first:dropout_transition=2[out]",
            "-map", "[out]",
            "-acodec", "pcm_s16le",
            str(mixed_audio)
        ]
        mix_result = subprocess.run(mix_cmd, capture_output=True, text=True)
        if mix_result.returncode != 0:
            print(f"  ⚠️  BGM混音失败: {mix_result.stderr[-200:]}")
            final_audio = audio_path
        else:
            final_audio = mixed_audio
            print(f"      混音完成 ✓")
    else:
        final_audio = audio_path

    # ─── 字幕时间 ───────────────────────────────
    # 如果有封面片头，字幕起始时间后移 COVER_DURATION
    has_cover = cover_path and cover_path.exists()
    cover_offset = COVER_DURATION if has_cover else 0.0
    
    total_chars = sum(len(s) for s in story_segments)
    sec_per_char = total_duration / total_chars if total_chars > 0 else 0.25
    actual_duration = total_duration + cover_offset

    # ── 先检查并确认可用的庞门正道字体 ──────────────
    pangmen_font = FONT_PANGMEN_TTF
    if not os.path.exists(pangmen_font):
        pangmen_font = FONT_SONG_HEAVY  # 回退到思源宋体
        print(f"  ⚠️  庞门正道字体不存在，回退到: {pangmen_font}")
    else:
        print(f"  🖌️  故事名字体: 庞门正道标题体 (毛笔飞白)")
    
    # ─── 构建 drawtext 滤镜链 ─────────────────────
    filter_parts = []
    
    # 故事名（独立显示，无装饰线包围，显示整个视频时长）
    safe_title = story_title.replace("'", "’").replace(":", "：")
    safe_title_esc = safe_title.replace("\\", "\\\\\\\\").replace("'", "\\\\'").replace(":", "\\\\:")
    title_decoration = (
        f"drawtext=fontfile={pangmen_font}:"
        f"text='— {safe_title_esc} —':"
        f"fontsize=96:"                          # 恢复96px
f"fontcolor=white@0.95:"                 # 白色，定稿版
        f"bordercolor=black@0.6:borderw=5:"
        f"shadowcolor=black@0.5:shadowx=3:shadowy=3:"
        f"x=(w-text_w)/2:"
        f"y=h*0.57:"                             # 去掉装饰线后微调居中
        f"enable='between(t,{COVER_DURATION},{actual_duration})'"  # 封面期间不显示，避免重叠
    )
    filter_parts.append(title_decoration)
    
    # 封面片头：大号故事名（封面3秒内单独显示，不与小标题重叠）
    if has_cover:
        cover_title = (
            f"drawtext=fontfile={pangmen_font}:"
            f"text='— {safe_title_esc} —':"
            f"fontsize=140:"                       # 封面大标题
            f"fontcolor=white@0.95:"
            f"bordercolor=black@0.7:borderw=8:"
            f"shadowcolor=black@0.6:shadowx=5:shadowy=5:"
            f"x=(w-text_w)/2:"
            f"y=h*0.55:"
            f"enable='between(t,0,{COVER_DURATION})'"
        )
        filter_parts.append(cover_title)
    
    current_time = 0.0 + cover_offset

    for i, seg in enumerate(story_segments):
        seg_duration = len(seg) * sec_per_char
        end_time = current_time + seg_duration

        enable_expr = f"between(t,{current_time:.2f},{end_time:.2f})"
        text = seg.replace("'", "’").replace(":", "：")
        # 转义ffmpeg特殊字符
        safe_text = text.replace("\\", "\\\\\\\\").replace("'", "\\\\'").replace(":", "\\\\:")

        # drawtext: 居中底部，字体大小64，黑色描边+阴影
        filter_part = (
            f"drawtext=fontfile={font_path}:"
            f"text='{safe_text}':"
            f"fontsize={SUB_FONT_SIZE}:"
            f"fontcolor=white:"
            f"bordercolor=black@0.85:borderw=6:"
            f"shadowcolor=black@0.7:shadowx=4:shadowy=4:"
            f"x=(w-text_w)/2:"
            f"y=h-text_h-420:"
            f"enable='{enable_expr}'"
        )
        filter_parts.append(filter_part)
        current_time = end_time

    vf_chain = ",".join(filter_parts) if filter_parts else "copy"

    # ─── FFmpeg 合成 ─────────────────────────────
    if scene_images and len(scene_images) == len(story_segments):
        # 多图模式：预先生成背景视频（逐段切换场景图）
        # 若有封面片头，封面作为第一帧插入
        print(f"  🖼️  多场景图模式: {len(scene_images)}张{' + 封面片头' if has_cover else ''}")
        
        seg_clips = []
        concat_lines = []
        
        # [封面片头] 如果有封面，插在第一帧（3秒）
        if has_cover:
            cover_clip = output_path.parent / ".cover_intro.mp4"
            cover_cmd = [
                "ffmpeg", "-y",
                "-loop", "1",
                "-i", str(cover_path),
                "-vf", "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:color=black,setsar=1",
                "-c:v", "libx264",
                "-tune", "stillimage",
                "-preset", "ultrafast",
                "-crf", "28",
                "-t", f"{COVER_DURATION:.3f}",
                "-pix_fmt", "yuv420p",
                "-an",
                str(cover_clip)
            ]
            subprocess.run(cover_cmd, capture_output=True, text=True, timeout=30)
            seg_clips.append(cover_clip)
            concat_lines.append(f"file '{cover_clip.name}'")
            print(f"     封面片头插入: {COVER_DURATION:.0f}s")
        
        # 生成逐段时长列表
        seg_times = []
        ctime = 0.0
        for i, seg in enumerate(story_segments):
            seg_dur = len(seg) * sec_per_char
            seg_times.append((i, str(scene_images[i]), ctime, ctime + seg_dur))
            ctime += seg_dur
        
        # 生成每个场景的视频clip → concat列表
        # 生成每个场景的视频clip → concat列表
        # 每个clip带 Ken Burns 缓动（慢速缩放+呼吸感微摆）
        ken_seed = abs(hash(story_title or "")) % 10000
        for idx, img_path, start, end in seg_times:
            clip_dur = end - start
            clip_path = output_path.parent / f".scene_{idx:02d}.mp4"
            
            # Ken Burns 参数（每张图随机但可复现）
            fps = 24
            total_frames = max(int(clip_dur * fps), 1)
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
                f"s={WIDTH}x{HEIGHT}:"
                f"fps={fps},"
                f"format=yuv420p"
            )
            
            clip_cmd = [
                "ffmpeg", "-y",
                "-i", str(img_path),
                "-vf", ken_burns_vf,
                "-c:v", "libx264",
                "-preset", "ultrafast",
                "-crf", "28",
                "-pix_fmt", "yuv420p",
                "-an",
                str(clip_path)
            ]
            subprocess.run(clip_cmd, capture_output=True, text=True, timeout=90)
            seg_clips.append(clip_path)
            concat_lines.append(f"file '{clip_path.name}'")
        
        # 用concat demuxer拼接所有clip
        concat_file = output_path.parent / ".concat_list.txt"
        concat_file.write_text("\n".join(concat_lines))
        
        concat_cmd = [
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0",
            "-i", str(concat_file),
            "-i", str(final_audio),
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", "23",
            "-c:a", "aac",
            "-b:a", "192k",
            "-vf", vf_chain,
            "-shortest",
            "-movflags", "+faststart",
            str(output_path)
        ]
        result = subprocess.run(concat_cmd, capture_output=True, text=True)
        
        # 清理临时文件
        for clip in seg_clips:
            try: clip.unlink()
            except: pass
        try: concat_file.unlink()
        except: pass
        
    else:
        # 单图模式
        use_bg = scene_images[0] if scene_images else bg_image_path
        cmd = [
            "ffmpeg", "-y",
            "-loop", "1",
            "-i", str(use_bg),
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
        print(f"  ❌ FFmpeg合成失败:")
        print(result.stderr[-800:])
        return False

    file_size = os.path.getsize(str(output_path)) / (1024 * 1024)
    print(f"  ✅ v7视频生成成功!")
    print(f"     路径: {output_path}")
    print(f"     大小: {file_size:.1f} MB")
    return True


# ═══════════════════════════════════════════════════════════════
#  主流程
# ═══════════════════════════════════════════════════════════════

async def main():
    parser = argparse.ArgumentParser(description="夜伴低语 v7 — 封面即背景 + 震撼BGM")
    parser.add_argument("--story", "-s", type=str, default=None)
    parser.add_argument("--voice", "-v", type=str, default=DEFAULT_VOICE)
    parser.add_argument("--output", "-o", type=str, default=None)
    parser.add_argument("--title", "-t", type=str, default="镜中人",
                        help="故事标题（封面大字）")
    parser.add_argument("--heartbeat", action="store_true",
                        help="BGM中加入心跳声")
    parser.add_argument("--no-bgm", action="store_true",
                        help="不添加背景音乐")
    parser.add_argument("--list-voices", action="store_true")
    args = parser.parse_args()

    ensure_dirs()

    if args.list_voices:
        print("\n📢 推荐中文恐怖故事配音:\n")
        print(f"  {'zh-CN-YunjianNeural':35s} - 深沉男声 ★推荐")
        print(f"  {'zh-CN-XiaoxiaoNeural':35s} - 温柔女声")
        print(f"  {'zh-CN-YunxiNeural':35s}    - 活力男声")
        print(f"  {'zh-CN-XiaoyiNeural':35s}   - 亲切女声")
        return

    # 加载故事
    if args.story:
        story_path = Path(args.story)
    else:
        story_path = STORIES_DIR / "sample_horror.txt"
        if not story_path.exists():
            sample_text = """半夜十二点，我接到一个电话。屏幕上显示的是十年前去世的母亲的号码。

我颤抖着接通，电话那头传来她熟悉的声音。她轻声说了一句话。

"别回头，他在你身后。"

我僵住了。身后的镜子里，映出了我的脸，还有另一个人的影子。

影子在笑。但我没有笑。"""
            story_path.write_text(sample_text.strip(), encoding="utf-8")
            print(f"  📝 已创建示例故事: {story_path}")

    if not story_path.exists():
        print(f"❌ 找不到故事文件: {story_path}")
        return

    raw_text = story_path.read_text(encoding="utf-8").strip()
    if not raw_text:
        print(f"❌ 故事文件为空")
        return

    story_title = args.title
    print(f"\n{'='*60}")
    print(f"  夜伴低语 v7 — 封面即背景 + 震撼BGM")
    print(f"{'='*60}")
    # 1. 清洗 + 分段
    raw_text = story_path.read_text(encoding="utf-8").strip()
    if not raw_text:
        print(f"❌ 故事文件为空")
        return
    
    # 检测是否含编剧[语气｜配乐｜画面]标签
    tagged_segments = parse_scribe_tags(raw_text)
    has_tags = len(tagged_segments) >= 3 and any(s['tone'] != '平静' for s in tagged_segments)
    
    if has_tags:
        print(f"  📋 检测到{len(tagged_segments)}段情感标签")
        # 标签版：直接用标签文本
        segments = [s['text'] for s in tagged_segments]
        text = '。'.join(segments)
        print(f"    {len(text)} 字, {len(tagged_segments)} 段")
        for i, seg in enumerate(tagged_segments, 1):
            print(f"      [{i}] [{seg['tone']}] {seg['text']}")
    else:
        # 无标签版：传统清洗+分段
        # 代码不再截断——字数控制由编剧铁律保障（≤1200字，保证3-4分钟完成）
        text = clean_text(raw_text)
        segments = split_into_segments(text)
        print(f"    {len(text)} 字, {len(segments)} 段")
        for i, seg in enumerate(segments, 1):
            print(f"      [{i}] {seg}")
    
    story_title = args.title or "未命名"
    print(f"📰 标题: 「{story_title}」")
    
    # 2. 生成配音
    raw_audio = AUDIO_DIR / f"{story_path.stem}_raw.mp3"
    
    if has_tags:
        duration = await generate_emotional_audio(
            tagged_segments, args.voice, raw_audio
        )
    else:
        duration = await generate_audio(text, args.voice, raw_audio)

    # 3. 语音后处理 — 仅无标签版做旧式处理（音高下移8% + Bass + 回声）
    #    标签版已有情感rate/pitch，跳过旧后处理以免破坏情绪
    if has_tags:
        final_audio_path = raw_audio
        print(f"  🎭 情感标签版：跳过旧式后处理，保留原生情绪")
    else:
        processed_audio = AUDIO_DIR / f"{story_path.stem}_processed.wav"
        final_audio_path_str = apply_voice_processing(raw_audio, processed_audio)
        final_audio_path = Path(final_audio_path_str)

    # 4. 使用可灵AI封面作为视频背景（代替手动绘制）
    kelin_bg = IMAGES_DIR / "kelin_cover_1080x1920.jpg"
    if kelin_bg.exists():
        bg_path = kelin_bg
        print(f"  🎨 使用可灵AI封面作为视频背景")
    else:
        # 回退到手动绘制
        bg_path = IMAGES_DIR / f"bg_{story_path.stem}_v7.jpg"
        create_story_background_with_title(
            bg_path,
            story_title=story_title,
            series_name="夜伴低语",
            seed=hash(story_path.name) % 10000
        )

    # 5. BGM — 多首真实恐怖BGM拼接
    bgm_path = None
    if not args.no_bgm:
        import glob, random as rnd
        bgm_files = sorted(glob.glob(str(AUDIO_DIR / "*.mp3")))
        # 排除配音相关的mp3文件和语音文件
        bgm_files = [f for f in bgm_files if 'sample_horror' not in f 
                     and 'yeban' not in f and 'test' not in f
                     and '_raw.mp3' not in f and '_ssml.mp3' not in f]
        if len(bgm_files) >= 2:
            # 多BGM交叉淡入淡出拼接
            bgm_path = combine_bgm_files(bgm_files, duration, VIDEOS_DIR)
        elif bgm_files:
            # 只有一首，直接使用（assemble里会循环补齐）
            bgm_path = Path(bgm_files[0])
            print(f"  🎵 BGM文件不足2首，单曲: {bgm_path.name}")
        else:
            print(f"  ⚠️  未找到真实BGM文件，跳过BGM")

    # 6. 视频合成
    output_name = args.output or f"yeban_v7_{story_path.stem}.mp4"
    output_path = VIDEOS_DIR / output_name
    
    # 检测画师的场景图片（scene_01.jpg, scene_02.jpg ...）
    scene_images = sorted(IMAGES_DIR.glob("scene_*.jpg"))
    if len(scene_images) == len(segments):
        print(f"  🖼️  检测到{len(scene_images)}张场景图，按段切换背景")
    elif scene_images:
        print(f"  ⚠️  场景图数量({len(scene_images)})与段落({len(segments)})不匹配，回退单图")
        scene_images = None
    else:
        scene_images = None
    
    # 夜伴低语封面（作为视频第一帧）
    kelin_cover = IMAGES_DIR / "kelin_cover_1080x1920.jpg"
    if not kelin_cover.exists():
        kelin_cover = IMAGES_DIR / "kelin_cover.jpg"
    has_cover = kelin_cover.exists()
    
    success = assemble_video_v7(
        final_audio_path, bg_path, segments, output_path,
        duration, story_title=story_title, bgm_path=bgm_path,
        heartbeat=args.heartbeat, scene_images=scene_images,
        cover_path=kelin_cover if has_cover else None
    )

    if success:
        print(f"\n{'='*60}")
        print(f"  ✅ 夜伴低语 v7 生成完成!")
        print(f"  📁 {output_path}")
        print(f"{'='*60}")
    else:
        print(f"\n❌ 生成失败")


if __name__ == "__main__":
    asyncio.run(main())
