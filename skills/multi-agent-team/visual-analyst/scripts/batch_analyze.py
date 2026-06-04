#!/usr/bin/env python3
"""Batch analyze all frames and generate visual analysis report.
Used when vision_analyze tool is unavailable (e.g., main model doesn't support images).
Bypasses Hermes vision_analyze by calling aliyun-bailian Qwen-VL API directly.

Usage:
    source ~/.hermes/.env 2>/dev/null && python3 batch_analyze.py

Environment variables (with defaults):
    FRAMES_DIR = video-inverse/frames/    # Input: frame images
    OUTPUT_DIR = video-inverse/output/   # Output: visual analysis report
    API_ENV_VAR = ALIYUN_BAILIAN_API_KEY  # API key env var name
    VISION_MODEL = qwen-vl-max-2025-08-13  # Vision model (帧捕手专用: 最高画质)
"""
import base64, json, os, sys, urllib.request
from collections import Counter
from datetime import datetime

# === Configuration ===
SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRAMES_DIR = os.environ.get("FRAMES_DIR") or os.path.join(
    SKILL_DIR.replace("/visual-analyst", "/video-inverse"), "frames")
OUTPUT_DIR = os.environ.get("OUTPUT_DIR") or os.path.join(
    SKILL_DIR.replace("/visual-analyst", "/video-inverse"), "output")
API_ENV_VAR = os.environ.get("API_ENV_VAR", "ALIYUN_BAILIAN_API_KEY")
VISION_MODEL = os.environ.get("VISION_MODEL", "qwen-vl-max-2025-08-13")
API_ENDPOINT = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
API_KEY = os.environ.get(API_ENV_VAR, "")

if not API_KEY:
    print(f"❌ {API_ENV_VAR} not set in environment")
    sys.exit(1)

os.makedirs(OUTPUT_DIR, exist_ok=True)

def analyze_frame(frame_path):
    with open(frame_path, "rb") as f:
        image_b64 = base64.b64encode(f.read()).decode("utf-8")
    
    prompt = """请详细描述这张画面的以下8个维度（用中文）：
1. 构图方式
2. 色彩调性（主色调HEX参考、色温冷/暖）
3. 照明方式（光源方向、强度、阴影）
4. 主体与物体
5. 动作与运动
6. 景深与焦点
7. 风格参考
8. 情感氛围

请以JSON格式输出，key为：构图, 色彩调性, 照明方式, 主体与物体, 动作与运动, 景深与焦点, 风格参考, 情感氛围"""

    payload = {
        "model": VISION_MODEL,
        "messages": [{"role": "user", "content": [
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}},
            {"type": "text", "text": prompt}
        ]}],
        "max_tokens": 800, "temperature": 0.1
    }
    
    req = urllib.request.Request(
        API_ENDPOINT,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
        method="POST"
    )
    
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            content = result["choices"][0]["message"]["content"]
            return {"success": True, "content": content}
    except Exception as e:
        return {"error": str(e)}

# === Run ===
frames = sorted([f for f in os.listdir(FRAMES_DIR) if f.endswith('.jpg')])
print(f"Total frames to analyze: {len(frames)}")

all_results = []
for i, frame_name in enumerate(frames):
    frame_path = os.path.join(FRAMES_DIR, frame_name)
    print(f"[{i+1}/{len(frames)}] {frame_name}...", end=" ")
    result = analyze_frame(frame_path)
    if result.get("success"):
        print("✅")
        all_results.append({"frame": frame_name, "analysis": result["content"]})
    else:
        print(f"❌ {result.get('error','')[:80]}")
        all_results.append({"frame": frame_name, "analysis": "ERROR", "error": result.get("error","")})

# === Generate report ===
lines = [f"# 🎨 画师视觉分析报告\n> 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n> 关键帧: {len(all_results)}\n"]

for item in all_results:
    lines.append(f"### {item['frame']}")
    if item.get("analysis") == "ERROR":
        lines.append(f"\n> ❌ 失败: {item.get('error','')}\n")
    else:
        try:
            data = json.loads(item["analysis"])
            for key in ["构图", "色彩调性", "照明方式", "主体与物体", "动作与运动", "景深与焦点", "风格参考", "情感氛围"]:
                val = data.get(key, "")
                if isinstance(val, dict):
                    detail = " · ".join([f"{k}: {v}" for k, v in val.items()])
                    lines.append(f"- **{key}**: {detail}")
                else:
                    lines.append(f"- **{key}**: {val}")
        except json.JSONDecodeError:
            lines.append(f"\n{item['analysis']}\n")
    lines.append("")

# Summary
styles, atms, comps, temps = [], [], [], []
for item in all_results:
    if item.get("analysis") != "ERROR":
        try:
            data = json.loads(item["analysis"])
            if data.get("风格参考"): styles.append(data["风格参考"])
            if data.get("情感氛围"): atms.append(data["情感氛围"])
            if data.get("构图"): comps.append(data["构图"])
            c = data.get("色彩调性", {})
            if isinstance(c, dict) and c.get("色温"): temps.append(c["色温"])
        except: pass

lines.append("## 综合视觉风格总结\n")
if styles:
    lines.append("### 风格分布\n" + "\n".join(f"- **{s}**: {c}/{len(frames)}帧" for s,c in Counter(styles).most_common(5)) + "\n")
if atms:
    lines.append("### 情感分布\n" + "\n".join(f"- **{a}**: {c}/{len(frames)}帧" for a,c in Counter(atms).most_common(5)) + "\n")
if comps:
    lines.append("### 构图分布\n" + "\n".join(f"- **{c[:40]}**: {cnt}/{len(frames)}帧" for c,cnt in Counter(comps).most_common(5)) + "\n")
if temps:
    lines.append("### 色温趋势\n" + "\n".join(f"- **{t}**: {c}/{len(frames)}帧" for t,c in Counter(temps).most_common(5)) + "\n")

report = "\n".join(lines)
report_path = os.path.join(OUTPUT_DIR, "visual_analysis.md")
with open(report_path, "w", encoding="utf-8") as f:
    f.write(report)
print(f"\n✅ Report: {report_path} ({len(report)} chars)")
