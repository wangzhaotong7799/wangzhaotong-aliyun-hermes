#!/usr/bin/env python3
"""
画师 — 批量场景图生成脚本
根据编剧标注的分段剧本，为每段场景调用通义万相生成暗黑漫画风图片

用法：
  python batch_generate_scenes.py story_01_守墓人_tagged.txt

输出：
  images/scene_01.jpg ~ scene_11.jpg
"""

import json, os, re, sys, time, requests
from pathlib import Path

# ─── 配置 ───────────────────────────────────────────────────
API_KEY = os.environ.get("ALIYUN_BAILIAN_API_KEY", "")
STYLE_PREFIX = "黑白漫画风格, 粗线条勾边, 高对比光影, 暗黑恐怖"
COLOR_TONE   = "黑灰白主色调, 少量血红点缀, 电影构图, 竖版"
IMAGE_DIR    = Path("images")
IMAGE_DIR.mkdir(exist_ok=True)

# ─── API调用 ────────────────────────────────────────────────

def generate_scene(scene_desc: str, scene_num: int) -> str | None:
    """调用通义万相生成一张场景图，返回本地路径"""
    prompt = f"{STYLE_PREFIX}, {scene_desc}, {COLOR_TONE}"
    
    # 提交任务
    r = requests.post(
        "https://dashscope.aliyuncs.com/api/v1/services/aigc/text2image/image-synthesis",
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "X-DashScope-Async": "enable",
            "Content-Type": "application/json",
        },
        json={
            "model": "wanx2.1-t2i-turbo",
            "input": {"prompt": prompt},
            "parameters": {"size": "1080*1920", "n": 1},
        },
        timeout=30,
    )
    data = r.json()
    if data.get("code"):
        print(f"  ❌ [{scene_num}] 提交失败: {data}")
        return None
    
    task_id = data["output"]["task_id"]
    print(f"  🎨 [{scene_num}] 任务已提交: {task_id}")

    # 轮询（约15-30秒出图）
    for i in range(30):
        r = requests.get(
            f"https://dashscope.aliyuncs.com/api/v1/tasks/{task_id}",
            headers={"Authorization": f"Bearer {API_KEY}"},
            timeout=15,
        )
        status = r.json()["output"]["task_status"]
        if status == "SUCCEEDED":
            img_url = r.json()["output"]["results"][0]["url"]
            save_path = IMAGE_DIR / f"scene_{scene_num:02d}.jpg"
            
            # 下载
            img_data = requests.get(img_url, timeout=30).content
            with open(save_path, "wb") as f:
                f.write(img_data)
            print(f"  ✅ [{scene_num}] 下载完成: {save_path} ({len(img_data)//1024}KB)")
            return str(save_path)
        elif status == "FAILED":
            print(f"  ❌ [{scene_num}] 生成失败: {r.json()}")
            return None
        
        print(f"  ⏳ [{scene_num}] 轮询中...({i+1}/30)")
        time.sleep(3)
    
    print(f"  ⚠️ [{scene_num}] 超时")
    return None


def parse_scene_descriptions(story_path: Path) -> list[dict]:
    """解析编剧剧本，提取每段的画面描述"""
    text = story_path.read_text(encoding="utf-8")
    lines = text.strip().split("\n")
    scenes = []
    
    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue
        m = re.match(r'\[([^\]]+)\]\s*(.*)', line)
        if m:
            tags = m.group(1).split("｜")
            scene_desc = tags[2].strip() if len(tags) > 2 else ""
            dialogue = m.group(2).strip()
            if scene_desc:
                scenes.append({
                    "num": i + 1,
                    "scene_desc": scene_desc,
                    "dialogue": dialogue[:30],
                })
    
    return scenes


def main():
    if len(sys.argv) < 2:
        print("用法: python batch_generate_scenes.py <story_tagged.txt>")
        sys.exit(1)
    
    story_path = Path(sys.argv[1])
    if not story_path.exists():
        print(f"❌ 文件不存在: {story_path}")
        sys.exit(1)
    
    if not API_KEY:
        print("❌ 未设置 ALIYUN_BAILIAN_API_KEY 环境变量")
        sys.exit(1)
    
    scenes = parse_scene_descriptions(story_path)
    print(f"📋 读取到 {len(scenes)} 段场景")
    
    for s in scenes:
        print(f"\n--- 场景 {s['num']}: {s['scene_desc']} ---")
        print(f"    台词: 「{s['dialogue']}」")
        generate_scene(s["scene_desc"], s["num"])
    
    print(f"\n✅ 完成! 图片在 {IMAGE_DIR}/")
    print(f"   共 {len(scenes)} 张，可传入导演合成")


if __name__ == "__main__":
    main()
