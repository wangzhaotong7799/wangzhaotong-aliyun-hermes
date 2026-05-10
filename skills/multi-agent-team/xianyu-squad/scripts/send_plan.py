#!/root/.hermes/hermes-agent/venv/bin/python3
"""
发送闲鱼90天执行计划Word文档到飞书
"""
import sys, os, json

MD_PATH = "/root/.hermes/skills/multi-agent-team/xianyu-squad/data/90day_plan.md"
DOCX_PATH = MD_PATH.replace(".md", ".docx")
CHAT_ID = "oc_10d032f2e5b7b86d660945627d981888"
CONFIG_PATH = "/root/.hermes/skills/multi-agent-team/wealth-analyst/scripts/md2word_config.json"

# ── 1. 用 md2word 转换 ──
from md2word import convert_file, Config

config = None
if os.path.exists(CONFIG_PATH):
    try:
        config = Config.from_file(CONFIG_PATH)
        print("📋 已加载排版配置")
    except Exception as e:
        print(f"⚠️ 配置加载失败: {e}")

try:
    if config:
        convert_file(MD_PATH, DOCX_PATH, config=config, toc=True)
    else:
        convert_file(MD_PATH, DOCX_PATH, toc=True)
    print(f"✅ Word 已生成: {DOCX_PATH}")
except Exception as e:
    print(f"❌ 转换失败: {e}")
    sys.exit(1)

# ── 2. 上传飞书 ──
import httpx

FEISHU_APP_ID = os.getenv("FEISHU_APP_ID", "")
FEISHU_APP_SECRET = os.getenv("FEISHU_APP_SECRET", "")

if not FEISHU_APP_ID or not FEISHU_APP_SECRET:
    print("❌ 缺少环境变量")
    sys.exit(1)

resp = httpx.post(
    "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
    json={"app_id": FEISHU_APP_ID, "app_secret": FEISHU_APP_SECRET},
    timeout=10
)
token = resp.json().get("tenant_access_token", "")
if not token:
    print(f"❌ Token获取失败")
    sys.exit(1)

headers = {"Authorization": f"Bearer {token}"}
file_name = os.path.basename(DOCX_PATH)

with open(DOCX_PATH, 'rb') as f:
    upload_resp = httpx.post(
        "https://open.feishu.cn/open-apis/im/v1/files",
        headers=headers,
        files={"file": (file_name, f, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
        data={"file_type": "doc", "file_name": file_name},
        timeout=30
    )

upload_data = upload_resp.json()
if upload_data.get("code") != 0:
    print(f"❌ 上传失败: {upload_data}")
    sys.exit(1)

file_key = upload_data["data"]["file_key"]

msg_resp = httpx.post(
    "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=chat_id",
    headers={**headers, "Content-Type": "application/json"},
    json={"receive_id": CHAT_ID, "msg_type": "file", "content": json.dumps({"file_key": file_key})},
    timeout=15
)

msg_data = msg_resp.json()
if msg_data.get("code") == 0:
    print(f"✅ Word文档已发送到飞书 ({file_name})")
else:
    print(f"❌ 发送失败: {msg_data}")
