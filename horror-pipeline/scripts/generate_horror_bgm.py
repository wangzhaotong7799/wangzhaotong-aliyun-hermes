#!/usr/bin/env python3
"""
恐怖BGM生成器 v3 - 带旋律的恐怖配乐
==============================
生成真正的恐怖背景音乐，包含:
  - 低频嗡鸣 (基础氛围)
  - 恐怖钢琴旋律 (小调，缓慢)
  - 弦乐垫 (慢速起伏)
  - 偶尔不和谐音
  - 可选心跳
"""

import math
import os
import random
import struct
import wave
from pathlib import Path

SAMPLE_RATE = 22050
CHANNELS = 1
SAMPLE_WIDTH = 2

# 小调音阶 (A minor)
# 用于生成恐怖旋律
MINOR_SCALE = {
    'root': 0,    # A2 = 110Hz
    'm2': 1,      # Bb
    'M2': 2,      # B
    'm3': 3,      # C
    'M3': 4,      # C#
    'P4': 5,      # D
    'd5': 6,      # Eb (三全音 = 最不和谐)
    'P5': 7,      # E
    'm6': 8,      # F
    'M6': 9,      # F#
    'm7': 10,     # G
    'M7': 11,     # G#
    'oct': 12,    # A3 = 220Hz
}

# 恐怖旋律常用音程（半音数）
TERROR_INTERVALS = [0, 3, 7, 10, 15, 17, 22]  # 根音、小三、纯五、小七、增八

# 半音到频率的转换
BASE_FREQ = 110  # A2


def note_to_freq(semitones: int) -> float:
    """半音数转频率"""
    return BASE_FREQ * (2 ** (semitones / 12))


def generate_horror_piano(duration: float, sr: int = SAMPLE_RATE,
                          density: float = 0.3) -> list:
    """
    生成恐怖钢琴旋律
    density: 音符密度 (0-1)，越高音符越多
    """
    n = int(sr * duration)
    result = [0.0] * n
    rng = random.Random(42)
    
    # 钢琴音符参数
    base_amp = 0.15
    
    # 在时间轴上撒音符
    current_time = 0
    min_gap = 1.5 - density  # 音符间隔 0.5~1.5秒
    
    while current_time < duration:
        # 选择音符（三全音、小调音程为主）
        semitones = rng.choice([0, 3, 5, 6, 7, 10, 13, 15, 17, 18, 22])
        freq = note_to_freq(semitones + rng.choice([0, 12, 24, -12]))  # 跨八度
        
        note_dur = rng.uniform(0.5, 2.0)
        note_start = int(current_time * sr)
        note_end = min(n, int((current_time + note_dur) * sr))
        note_len = note_end - note_start
        
        # 钢琴音色：快速衰减
        for i in range(note_len):
            pos = note_start + i
            if pos >= n:
                break
            # 钢琴包络：快速起音 + 缓慢衰减
            env = math.exp(-i / (sr * 0.3))  # 300ms 衰减
            if env < 0.01:
                break
            # 加一些泛音，更丰富
            fundamental = math.sin(2 * math.pi * freq * i / sr)
            overtone1 = 0.3 * math.sin(2 * math.pi * freq * 2 * i / sr)
            overtone2 = 0.1 * math.sin(2 * math.pi * freq * 3 * i / sr)
            result[pos] += base_amp * env * (fundamental + overtone1 + overtone2) * 0.7
        
        # 下一个音符的时间
        gap = rng.uniform(min_gap, min_gap + 1.5)
        current_time += note_dur + gap
    
    return result


def generate_string_pad(duration: float, sr: int = SAMPLE_RATE) -> list:
    """
    生成弦乐垫（缓慢起伏的氛围弦乐）
    """
    n = int(sr * duration)
    result = [0.0] * n
    rng = random.Random(43)
    
    # 选择几个和弦音
    # 使用小调和弦：Am (A,C,E), Dm (D,F,A), Em (E,G,B), F (F,A,C)
    chords = [
        [0, 3, 7],     # Am
        [5, 8, 12],    # Dm
        [7, 10, 14],   # Em
        [8, 12, 15],   # F
        [3, 6, 10],    # Cdim (减三，非常不和谐)
    ]
    
    chord_dur = rng.uniform(4, 8)  # 每个和弦持续4-8秒
    current_time = 0
    
    while current_time < duration:
        chord = rng.choice(chords)
        chord_end = min(duration, current_time + chord_dur)
        chord_start_sample = int(current_time * sr)
        chord_end_sample = int(chord_end * sr)
        
        for semi in chord:
            freq = note_to_freq(semi - 12)  # 低八度
            freq2 = note_to_freq(semi)       # 原八度
            
            for i in range(chord_start_sample, chord_end_sample):
                pos = i
                if pos >= n:
                    break
                t = (pos - chord_start_sample) / sr
                chord_progress = (pos - chord_start_sample) / (chord_end_sample - chord_start_sample)
                
                # 缓慢的振幅调制（弦乐颤音效果）
                amp_mod = 0.7 + 0.3 * math.sin(2 * math.pi * 0.15 * t)
                
                # 淡入淡出跨和弦过渡
                fade = min(1.0, chord_progress * 4, (1 - chord_progress) * 4)
                
                # 添加锯齿波（弦乐质感）
                saw = 2 * (freq * t - math.floor(freq * t + 0.5))
                saw2 = 2 * (freq2 * t - math.floor(freq2 * t + 0.5))
                
                # 混合正弦+锯齿
                tone = (0.4 * math.sin(2 * math.pi * freq * t) +
                       0.4 * saw +
                       0.2 * math.sin(2 * math.pi * freq2 * t))
                
                result[pos] += 0.04 * amp_mod * fade * tone
        
        current_time += chord_dur
        chord_dur = rng.uniform(4, 8)
    
    return result


def generate_bass_drone(duration: float, sr: int = SAMPLE_RATE) -> list:
    """低音嗡鸣（更低沉，带次谐波）"""
    n = int(sr * duration)
    result = [0.0] * n
    
    # 极低频 (30-50Hz)
    freq = 35
    for t in range(n):
        env = min(1.0, t / (sr * 0.5), (n - t) / (sr * 0.5))
        # 次谐波失真（产生更黑暗的音色）
        sine = math.sin(2 * math.pi * freq * t / sr)
        sub = math.sin(2 * math.pi * (freq / 2) * t / sr) * 0.3
        result[t] += (sine + sub) * 0.2 * env
    
    return result


def generate_atonal_swell(duration: float, sr: int = SAMPLE_RATE) -> list:
    """偶尔的不和谐音高潮（恐怖片经典）"""
    n = int(sr * duration)
    result = [0.0] * n
    rng = random.Random(44)
    
    num_swells = rng.randint(2, 4)
    for _ in range(num_swells):
        start = rng.randint(int(sr * 3), n - int(sr * 2))
        swell_dur = rng.uniform(0.8, 2.0)
        swell_end = min(n, start + int(swell_dur * sr))
        
        # 一组不和谐频率簇
        freqs = [rng.uniform(200, 800) for _ in range(rng.randint(3, 6))]
        
        for i in range(start, swell_end):
            t = (i - start) / (swell_end - start)
            # 先渐强后渐弱
            env = math.sin(math.pi * t)
            sample = sum(math.sin(2 * math.pi * f * (i - start) / sr) 
                        for f in freqs) / len(freqs)
            result[i] += 0.06 * env * sample
    
    return result


def generate_wind_noise(duration: float, sr: int = SAMPLE_RATE) -> list:
    """风噪声"""
    n = int(sr * duration)
    rng = random.Random(45)
    result = [0.0] * n
    
    for t in range(0, n, sr // 30):
        chunk_end = min(t + sr // 30, n)
        amp = 0.015 + 0.025 * (0.5 + 0.5 * math.sin(2 * math.pi * 0.04 * t / sr))
        for i in range(t, chunk_end):
            result[i] += rng.uniform(-1, 1) * amp
    
    return result


def generate_heartbeat(duration: float, bpm: int = 65, 
                       sr: int = SAMPLE_RATE) -> list:
    """心跳声"""
    n = int(sr * duration)
    result = [0.0] * n
    
    beat_interval = int(60.0 / bpm * sr)
    lub_len = int(0.08 * sr)
    dub_offset = int(0.12 * sr)
    dub_len = int(0.05 * sr)
    
    for beat_start in range(int(sr * 2), n, beat_interval):
        # lub
        for i in range(lub_len):
            pos = beat_start + i
            if pos < n:
                env = math.sin(math.pi * i / lub_len)
                result[pos] += 0.10 * env * math.sin(2 * math.pi * 60 * i / sr)
        # dub
        for i in range(dub_len):
            pos = beat_start + dub_offset + i
            if pos < n:
                env = math.sin(math.pi * i / dub_len)
                result[pos] += 0.07 * env * math.sin(2 * math.pi * 75 * i / sr)
    
    return result


def generate_bgm(duration: float, sr: int = SAMPLE_RATE,
                 include_heartbeat: bool = False,
                 style: str = "full") -> list:
    """
    合成完整恐怖配乐
    
    style 参数:
      "full"   - 全部元素 (钢琴+弦乐+低音+不和谐+风噪)
      "ambient" - 仅氛围 (低音+风噪)
      "melodic" - 偏旋律 (钢琴+弦乐为主)
    """
    n = int(sr * duration)
    
    print(f"  🎵 合成恐怖配乐 v3...")
    print(f"      风格={style}, 时长={duration:.1f}s, 心率={'有' if include_heartbeat else '无'}")
    
    # 各层生成
    layers = {}
    
    if style in ("full", "ambient"):
        layers['bass'] = generate_bass_drone(duration, sr)
        print(f"      低音嗡鸣 ✅")
        layers['wind'] = generate_wind_noise(duration, sr)
        print(f"      风噪声   ✅")
    
    if style in ("full", "melodic"):
        layers['piano'] = generate_horror_piano(duration, sr, density=0.3)
        print(f"      钢琴旋律 ✅")
        layers['strings'] = generate_string_pad(duration, sr)
        print(f"      弦乐垫   ✅")
        layers['swell'] = generate_atonal_swell(duration, sr)
        print(f"      不和谐音 ✅")
    
    if include_heartbeat:
        layers['heart'] = generate_heartbeat(duration, sr)
        print(f"      心跳声   ✅")
    
    # 混合
    result = [0.0] * n
    for name, samples in layers.items():
        for i in range(min(n, len(samples))):
            result[i] += samples[i]
    
    # 归一化
    max_val = max(abs(s) for s in result) or 1.0
    if max_val > 0.6:
        result = [s * 0.6 / max_val for s in result]
    
    return result


def save_wav(samples: list, output_path: Path, sr: int = SAMPLE_RATE):
    """保存为 WAV"""
    n_samples = len(samples)
    with wave.open(str(output_path), 'w') as wav:
        wav.setnchannels(CHANNELS)
        wav.setsampwidth(SAMPLE_WIDTH)
        wav.setframerate(sr)
        for s in samples:
            int_val = int(max(-32768, min(32767, s * 32767)))
            wav.writeframes(struct.pack('<h', int_val))
    
    size = os.path.getsize(str(output_path)) / 1024
    print(f"  ✅ BGM保存: {output_path.name} ({size:.0f}KB)")


def generate(duration: float, output_path: Path = None,
             heartbeat: bool = False, style: str = "full",
             sr: int = SAMPLE_RATE):
    """一键生成"""
    samples = generate_bgm(duration + 1, sr, heartbeat, style)
    if output_path:
        save_wav(samples, output_path, sr)
        return str(output_path)
    return samples


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="恐怖配乐生成器 v3")
    parser.add_argument("--duration", "-d", type=float, default=30)
    parser.add_argument("--output", "-o", type=str, default=None)
    parser.add_argument("--heartbeat", action="store_true")
    parser.add_argument("--style", "-s", choices=["full", "ambient", "melodic"],
                        default="full", help="配乐风格")
    args = parser.parse_args()
    
    out_dir = Path(__file__).resolve().parent.parent / "audio"
    out_dir.mkdir(parents=True, exist_ok=True)
    
    style_tag = {"full": "", "ambient": "_ambient", "melodic": "_melodic"}[args.style]
    out_path = Path(args.output) if args.output else \
        out_dir / f"horror_bgm{style_tag}_{int(args.duration)}s.wav"
    
    generate(args.duration, out_path, args.heartbeat, args.style)
