#!/root/.hermes/hermes-agent/venv/bin/python3
"""将 Markdown 报告转为 Word 并上传飞书

用法: python3 md_to_feishu_docx.py <md文件路径> [飞书聊天ID]

需要环境变量: FEISHU_APP_ID, FEISHU_APP_SECRET
"""
import re, os, sys, json, subprocess

MD_PATH = sys.argv[1] if len(sys.argv) > 1 else ""
CHAT_ID = sys.argv[2] if len(sys.argv) > 2 else os.getenv("FEISHU_CHAT_ID", "oc_99961a56e530e89f7e369cd6ecb50218")

if not MD_PATH or not os.path.exists(MD_PATH):
    print(f"❌ 文件不存在: {MD_PATH}")
    sys.exit(1)

# 1. 转换 MD → DOCX
DOCX_PATH = MD_PATH.replace(".md", ".docx")

from docx import Document
from docx.shared import Pt

with open(MD_PATH, 'r') as f:
    lines = f.readlines()

doc = Document()
style = doc.styles['Normal']
font = style.font
font.name = 'Arial'
font.size = Pt(10.5)

in_table = False
table_rows = []

def flush_table():
    global in_table, table_rows
    if not in_table or len(table_rows) < 2:
        return
    max_cols = max(len(r) for r in table_rows)
    t = doc.add_table(rows=len(table_rows), cols=max_cols)
    t.style = 'Light Grid Accent 1'
    for i, row_data in enumerate(table_rows):
        for j, cell_text in enumerate(row_data):
            if j < max_cols:
                cell = t.rows[i].cells[j]
                cell.text = cell_text[:200]
                for para in cell.paragraphs:
                    for run in para.runs:
                        run.font.size = Pt(9)
                        if i == 0:
                            run.bold = True
    in_table = False
    table_rows = []
    doc.add_paragraph('')

for line in lines:
    s = line.rstrip()
    if s.startswith('# ') and not s.startswith('## '):
        flush_table()
        h = doc.add_heading('', level=0)
        r = h.add_run(s.replace('# ', ''))
        r.font.size = Pt(18)
    elif s.startswith('## ') and not s.startswith('### '):
        flush_table()
        doc.add_heading(s.replace('## ', ''), level=1)
    elif s.startswith('### '):
        flush_table()
        doc.add_heading(s.replace('### ', ''), level=2)
    elif s.startswith('|') and s.endswith('|'):
        cells = [c.strip() for c in s.split('|')[1:-1]]
        if all(re.match(r'^:?-+:?$', c.replace(':', '').strip()) for c in cells if c.strip()):
            continue
        if not in_table:
            in_table = True
            table_rows = []
        table_rows.append(cells)
    else:
        flush_table()
        if not s:
            continue
        clean = re.sub(r'\*\*(.*?)\*\*', r'\1', s)
        clean = re.sub(r'[🥇🥈🥉]', '', clean)
        clean = re.sub(r'^\s*\d+\|', '', clean).strip()
        if clean:
            doc.add_paragraph(clean)

flush_table()
doc.save(DOCX_PATH)
print(f"✅ Word 已生成: {DOCX_PATH}")

# 2. 获取飞书 Token
FEISHU_APP_ID = os.getenv("FEISHU_APP_ID", "")
FEISHU_APP_SECRET = os.getenv("FEISHU_APP_SECRET", "")
if not FEISHU_APP_ID or not FEISHU_APP_SECRET:
    print("❌ 缺少 FEISHU_APP_ID 或 FEISHU_APP_SECRET")
    sys.exit(1)

import httpx

# 获取 tenant_access_token
resp = httpx.post("https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal", json={
    "app_id": FEISHU_APP_ID,
    "app_secret": FEISHU_APP_SECRET
}, timeout=10)
token = resp.json().get("tenant_access_token", "")
if not token:
    print(f"❌ 获取 Token 失败: {resp.text}")
    sys.exit(1)

# 3. 上传文件到飞书
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

# 4. 发送文件消息
msg_resp = httpx.post(
    f"https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=chat_id",
    headers={**headers, "Content-Type": "application/json"},
    json={
        "receive_id": CHAT_ID,
        "msg_type": "file",
        "content": json.dumps({"file_key": file_key})
    },
    timeout=15
)

msg_data = msg_resp.json()
if msg_data.get("code") == 0:
    print(f"✅ Word 文档已发送到飞书 ({file_name})")
else:
    print(f"❌ 发送失败: {msg_data}")
    sys.exit(1)
