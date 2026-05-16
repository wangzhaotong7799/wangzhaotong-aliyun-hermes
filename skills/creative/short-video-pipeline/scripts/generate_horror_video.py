#!/usr/bin/env python3
"""
恐怖故事短视频生成器 v0.3 - 含BGM
v0.3: +BGM生成+混音, +drawtext中文字幕(指定fontfile), +暗黑渐变背景
"""
import argparse, asyncio, math, os, random, re, subprocess, textwrap
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
STORIES_DIR, AUDIO_DIR, IMAGES_DIR, VIDEOS_DIR, SCRIPTS_DIR = (
    PROJECT_DIR/d for d in ["stories","audio","images","videos","scripts"]
)

CHINESE_FONTS = [
    "/usr/share/fonts/wqy-microhei/wqy-microhei.ttc",
    "/usr/share/fonts/google-noto-cjk/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/google-noto-cjk/NotoSansCJK-Regular.ttc",
]
DEFAULT_VOICE = "zh-CN-YunjianNeural"
W, H, FONT_SIZE = 1080, 1920, 52

def find_cn_font():
    for fp in CHINESE_FONTS:
        if os.path.exists(fp): return fp
    raise RuntimeError("无中文字体，请装 wqy-microhei-fonts")

async def generate_audio(text, voice, path):
    import edge_tts
    print(f"  🎙️  {voice}")
    await edge_tts.Communicate(text, voice).save(str(path))
    r = subprocess.run(["ffprobe","-v","error","-show_entries","format=duration","-of","default=noprint_wrappers=1:nokey=1",str(path)], capture_output=True, text=True)
    d = float(r.stdout.strip() or 0)
    print(f"      {d:.1f}s"); return d

def create_bg(path, seed=None):
    from PIL import Image, ImageDraw, ImageFilter, ImageEnhance
    rng = random.Random(seed)
    print("  🎨 背景")
    img = Image.new("RGB", (W, H), (0,0,0))
    cx, cy = W//2, H//3
    mr = int(math.sqrt(cx**2+max(cy,H-cy)**2))+100
    draw = ImageDraw.Draw(img)
    for r in range(mr,0,-1):
        t = r/mr
        if t<.3: c = (35,5,8)
        elif t<.6: c = tuple(int(a+(b-a)*(t-.3)/.3) for a,b in zip((35,5,8),(18,3,5)))
        else: c = tuple(int(a+(b-a)*(t-.6)/.4) for a,b in zip((18,3,5),(2,1,2)))
        draw.ellipse([cx-r*1.1,cy-r*1.5,cx+r*1.1,cy+r*1.5], fill=c)
    fog = Image.new("RGB", (W,H), (0,0,0))
    fd = ImageDraw.Draw(fog)
    for _ in range(15000):
        x,y = rng.randint(0,W-1), rng.randint(0,H-1)
        d = math.sqrt((x-cx)**2+(y-cy*.7)**2)/mr
        if d>1: continue
        v = rng.randint(0,max(1,int(25*(1-d))))
        fd.point((x,y),(v,v//2,v//3))
    img = Image.blend(img, fog.filter(ImageFilter.GaussianBlur(8)), 0.4)
    vig = Image.new("RGB",(W,H),(0,0,0))
    vd = ImageDraw.Draw(vig)
    for r in range(int(mr*1.5),int(mr*.4),-1):
        t = (r-mr*.4)/(mr*1.1)
        if t<0: continue
        a = int(255*min(1,t*.8))
        vd.ellipse([cx-r,cy-r*1.3,cx+r,cy+r*1.3], fill=(a,a,a))
    vig = vig.filter(ImageFilter.GaussianBlur(30))
    vg = [max(rgb) for rgb in vig.getdata()]
    mv = max(vg) or 255
    mask = Image.new('L',(W,H))
    mask.putdata([int(255-g*.6/mv*255) for g in vg])
    img = Image.composite(img, Image.new("RGB",(W,H),(0,0,0)), mask)
    cd = ImageDraw.Draw(img)
    for _ in range(rng.randint(3,6)):
        x,y = rng.randint(0,W-1),rng.randint(0,H-1)
        l,a = rng.randint(50,200),rng.uniform(0,2*math.pi)
        for s in range(l):
            nx,ny = int(x+s*math.cos(a)+rng.gauss(0,3)),int(y+s*math.sin(a)+rng.gauss(0,3))
            if 0<=nx<W and 0<=ny<H: cd.point((nx,ny),(rng.randint(5,15),rng.randint(1,5),rng.randint(1,4)))
    img = ImageEnhance.Brightness(img.filter(ImageFilter.GaussianBlur(1))).enhance(.85)
    px = img.load()
    for x in range(W):
        for y in range(H):
            r,g,b=px[x,y]; px[x,y]=(max(0,r-2),max(0,g-1),min(255,b+1))
    img.save(str(path), quality=92)
    print(f"     {path.name}")

def clean_text(text, max_c=500):
    text = re.sub(r'\s+',' ',text).strip()
    if len(text)>max_c:
        c=max_c
        for p in '。！？.!?':
            pos=text.rfind(p,0,c)
            if pos>max_c*.6: c=pos+1; break
        text=text[:c]
    return text

def split_segments(text, ml=35):
    ss,b=[],""
    for c in text:
        b+=c
        if c in '。！？.!?' and len(b)>=5:
            ss.append(b.strip()); b=""
    if b.strip(): ss.append(b.strip())
    if not ss: ss=[text]
    r=[]
    for s in ss:
        s=s.strip()
        if not s: continue
        if len(s)<=ml: r.append(s)
        else: r.extend(textwrap.wrap(s,width=ml))
    return r or [text]

def assemble_video(audio_path, bg_path, segments, out_path, duration, bgm_path=None):
    print("  🎬 合成...")
    fp = find_cn_font()
    if bgm_path and bgm_path.exists():
        mixed = out_path.parent/f"{out_path.stem}_mixed.wav"
        r = subprocess.run(["ffmpeg","-y","-i",str(audio_path),"-i",str(bgm_path),
            "-filter_complex","[1:a]volume=0.18[bgm];[0:a][bgm]amix=inputs=2:duration=first:dropout_transition=2[out]",
            "-map","[out]","-acodec","pcm_s16le",str(mixed)], capture_output=True, text=True)
        final_audio = mixed if r.returncode==0 else audio_path
        if r.returncode==0: print("     BGM混音完成")
    else: final_audio=audio_path
    tc=sum(len(s) for s in segments)
    spc=duration/tc if tc>0 else .25
    fps,ct=[],0.0
    for seg in segments:
        et=ct+len(seg)*spc
        t=seg.replace("'","’").replace(":","：")
        fps.append(f"drawtext=fontfile={fp}:text='{t}':fontsize={FONT_SIZE}:fontcolor=white:bordercolor=black@0.8:borderw=4:shadowcolor=black@0.6:shadowx=3:shadowy=3:x=(w-text_w)/2:y=h-text_h-120:enable='between(t,{ct:.2f},{et:.2f})'")
        ct=et
    vf = ",".join(fps) if fps else "copy"
    r=subprocess.run(["ffmpeg","-y","-loop","1","-i",str(bg_path),"-i",str(final_audio),
        "-c:v","libx264","-tune","stillimage","-preset","medium","-crf","23",
        "-c:a","aac","-b:a","192k","-pix_fmt","yuv420p","-vf",vf,"-shortest","-movflags","+faststart",str(out_path)],
        capture_output=True,text=True)
    if r.returncode!=0: print(f"  ❌ {r.stderr[-500:]}"); return False
    print(f"  ✅ {out_path.name} ({os.path.getsize(str(out_path))/1024/1024:.1f}MB)")
    return True

async def main():
    p=argparse.ArgumentParser()
    p.add_argument("--story","-s"); p.add_argument("--voice","-v",default=DEFAULT_VOICE)
    p.add_argument("--output","-o"); p.add_argument("--list-voices",action="store_true")
    p.add_argument("--bgm",action="store_true"); p.add_argument("--heartbeat",action="store_true")
    a=p.parse_args()
    for d in [STORIES_DIR,AUDIO_DIR,IMAGES_DIR,VIDEOS_DIR]: d.mkdir(parents=True,exist_ok=True)
    if a.list_voices:
        for v,d in [("zh-CN-YunjianNeural","深沉男声★"),("zh-CN-XiaoxiaoNeural","温柔女声"),("zh-CN-YunxiNeural","活力男声"),("zh-CN-XiaoyiNeural","亲切女声")]: print(f"  {v:35s} - {d}")
        return
    sp = Path(a.story) if a.story else STORIES_DIR/"sample_horror.txt"
    if not sp.exists():
        sp.write_text("""那是一个雨夜，我独自走在回家的路上。路灯忽明忽灭，地上的积水映着昏暗的光。""",encoding="utf-8")
    raw = sp.read_text(encoding="utf-8").strip()
    if not raw: print("❌ 空文件"); return
    print(f"\n📖 {sp.name}")
    text=clean_text(raw); segs=split_segments(text)
    print(f"   {len(text)}字, {len(segs)}段")
    audio_path=AUDIO_DIR/f"{sp.stem}.mp3"
    dur=await generate_audio(text,a.voice,audio_path)
    bg_path=IMAGES_DIR/f"bg_{sp.stem}.jpg"
    create_bg(bg_path,hash(sp.name)%10000)
    bgm_path=None
    if a.bgm:
        print("  🎵 BGM")
        sys.path.insert(0,str(SCRIPTS_DIR))
        from generate_horror_bgm import generate_bgm, save_wav
        bgm_path=AUDIO_DIR/f"horror_bgm_{int(dur)+5}s.wav"
        s=generate_bgm(dur+5,heartbeat=a.heartbeat)
        save_wav(s,bgm_path)
        print(f"     {bgm_path.name}")
    out_path=VIDEOS_DIR/(a.output or f"{sp.stem}_v3.mp4")
    success=assemble_video(audio_path,bg_path,segs,out_path,dur,bgm_path)
    if success: print(f"\n✅ {out_path}")

import sys
if __name__=="__main__": asyncio.run(main())
