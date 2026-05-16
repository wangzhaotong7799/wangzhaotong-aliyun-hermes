#!/usr/bin/env python3
"""
恐怖BGM生成器 v2 - 轻量快速版
合成恐怖氛围音: 低频嗡鸣+风噪+不和谐高音+心跳
输出: WAV, 22050Hz, 16-bit, mono

用法:
  python3 generate_horror_bgm.py --duration 30 --heartbeat
"""

import math, os, struct, wave, random
from pathlib import Path

SAMPLE_RATE, CHANNELS, SAMPLE_WIDTH = 22050, 1, 2
_SIN_CACHE = {}

def _sin_wave(freq, length, sr):
    key = (freq, length, sr)
    if key not in _SIN_CACHE:
        _SIN_CACHE[key] = [math.sin(2*math.pi*freq*t/sr) for t in range(length)]
    return _SIN_CACHE[key]

def generate_bgm(duration, sr=SAMPLE_RATE, heartbeat=False):
    n = int(sr * duration)
    result = [0.0] * n
    # 1. 低频嗡鸣
    d1, d2 = _sin_wave(50, n, sr), _sin_wave(61, n, sr)
    for t in range(n):
        amp = 0.5 + 0.5*math.sin(2*math.pi*0.08*t/sr)
        env = min(1.0, t/(sr*0.3), (n-t)/(sr*0.3))
        result[t] += (d1[t]*0.25 + d2[t]*0.12) * env * amp
    # 2. 风噪
    rng = random.Random(42)
    for t in range(0, n, sr//20):
        ch_end = min(t+sr//20, n)
        na = 0.02 + 0.03*(0.5+0.5*math.sin(2*math.pi*0.03*t/sr))
        for i in range(t, ch_end):
            result[i] += rng.uniform(-1,1)*na
    # 3. 不和谐高音
    for _ in range(random.randint(2,4)):
        st = random.randint(sr, n-int(sr*1.5))
        nd = random.uniform(0.5,1.2)
        f = random.choice([430,470,540,660,780])
        note = _sin_wave(f, int(sr*nd), sr)
        for i,s in enumerate(note):
            p = st+i
            if p>=n: break
            result[p] += s*0.03*math.sin(math.pi*i/len(note))
    # 4. 心跳
    if heartbeat:
        bi = int(60/65*sr)
        for bs in range(sr, n, bi):
            for i in range(int(0.08*sr)):
                p=bs+i
                if p<n: result[p] += 0.12*math.sin(math.pi*i/(0.08*sr))*math.sin(2*math.pi*60*i/sr)
            for i in range(int(0.05*sr)):
                p=bs+int(0.12*sr)+i
                if p<n: result[p] += 0.08*math.sin(math.pi*i/(0.05*sr))*math.sin(2*math.pi*70*i/sr)
    mx = max(abs(s) for s in result) or 1.0
    if mx > 0.8: result = [s*0.8/mx for s in result]
    return result

def save_wav(samples, path, sr=SAMPLE_RATE):
    with wave.open(str(path),'w') as w:
        w.setnchannels(CHANNELS); w.setsampwidth(SAMPLE_WIDTH); w.setframerate(sr)
        for s in samples:
            w.writeframes(struct.pack('<h', int(max(-32768,min(32767,s*32767)))))

if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--duration","-d",type=float,default=30)
    p.add_argument("--output","-o",type=str)
    p.add_argument("--heartbeat",action="store_true")
    a = p.parse_args()
    out = Path(a.output) if a.output else Path(f"horror_bgm_{int(a.duration)}s.wav")
    print(f"合成BGM {a.duration}s{' 有心跳' if a.heartbeat else ''}")
    s = generate_bgm(a.duration, heartbeat=a.heartbeat)
    save_wav(s, out)
    print(f"OK: {out} ({os.path.getsize(out)//1024}KB)")
