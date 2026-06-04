#!/root/.hermes/hermes-agent/venv/bin/python3
"""
Send a file (TXT/DOCX/etc) to Feishu as a file attachment.

Usage:
  python3 send_feishu_file.py <file_path> [chat_id] [file_name]

Args:
  file_path: Path to the file to upload and send
  chat_id:   (optional) Feishu chat ID. Default: oc_10d032f2e5b7b86d660945627d981888
  file_name: (optional) Display name in Feishu. Default: basename of file_path

Environment:
  FEISHU_APP_ID, FEISHU_APP_SECRET from ~/.hermes/.env

Examples:
  # Send TXT file
  python3 send_feishu_file.py /tmp/汤泉粮子洗浴中心规则怪谈.txt
  
  # Send with custom chat ID and file name
  python3 send_feishu_file.py data/report.md oc_xxx报告.docx
"""
import json, os, sys, mimetypes, urllib.request

# Defaults
DEFAULT_CHAT_ID = "oc_10d032f2e5b7b86d660945627d981888"
ENV_FILE = os.path.expanduser("~/.hermes/.env")

def load_env():
    """Load environment variables from .env file"""
    if not os.path.exists(ENV_FILE):
        print(f"Error: {ENV_FILE} not found", file=sys.stderr)
        sys.exit(1)
    with open(ENV_FILE) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ[k.strip()] = v.strip()

def get_token():
    """Get Feishu tenant_access_token"""
    payload = json.dumps({
        "app_id": os.environ["FEISHU_APP_ID"],
        "app_secret": os.environ["FEISHU_APP_SECRET"]
    }).encode()
    req = urllib.request.Request(
        "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
        data=payload,
        headers={"Content-Type": "application/json"}
    )
    resp = json.loads(urllib.request.urlopen(req).read())
    token = resp.get("tenant_access_token", "")
    if not token:
        print(f"Error getting token: {resp}", file=sys.stderr)
        sys.exit(1)
    return token

def upload_file(token, file_path, file_name):
    """Upload file to Feishu and get file_key"""
    with open(file_path, "rb") as f:
        file_data = f.read()
    
    boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
    
    body_parts = []
    body_parts.append(f"--{boundary}\r\n")
    body_parts.append('Content-Disposition: form-data; name="file_type"\r\n\r\n')
    body_parts.append("stream\r\n")
    body_parts.append(f"--{boundary}\r\n")
    body_parts.append(f'Content-Disposition: form-data; name="file_name"\r\n\r\n')
    body_parts.append(f"{file_name}\r\n")
    body_parts.append(f"--{boundary}\r\n")
    body_parts.append(f'Content-Disposition: form-data; name="file"; filename="{file_name}"\r\n')
    # Detect MIME type
    mime_type, _ = mimetypes.guess_type(file_name)
    body_parts.append(f"Content-Type: {mime_type or 'application/octet-stream'}\r\n\r\n")
    
    body = "".join(body_parts).encode("utf-8") + file_data + f"\r\n--{boundary}--\r\n".encode("utf-8")
    
    req = urllib.request.Request(
        "https://open.feishu.cn/open-apis/im/v1/files",
        data=body,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": f"multipart/form-data; boundary={boundary}"
        }
    )
    resp = json.loads(urllib.request.urlopen(req).read())
    if resp.get("code") != 0:
        print(f"Upload error: {resp}", file=sys.stderr)
        sys.exit(1)
    return resp["data"]["file_key"]

def send_file_message(token, chat_id, file_key):
    """Send file message to Feishu chat"""
    content = json.dumps({"file_key": file_key}, ensure_ascii=False)
    payload = json.dumps({
        "receive_id": chat_id,
        "msg_type": "file",
        "content": content
    }, ensure_ascii=False).encode("utf-8")
    
    req = urllib.request.Request(
        f"https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=chat_id",
        data=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8"
        }
    )
    resp = json.loads(urllib.request.urlopen(req).read())
    if resp.get("code") != 0:
        print(f"Send error: {resp}", file=sys.stderr)
        sys.exit(1)
    return resp

def main():
    if len(sys.argv) < 2:
        print(__doc__, file=sys.stderr)
        sys.exit(1)
    
    file_path = sys.argv[1]
    chat_id = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_CHAT_ID
    file_name = sys.argv[3] if len(sys.argv) > 3 else os.path.basename(file_path)
    
    if not os.path.exists(file_path):
        print(f"Error: File not found: {file_path}", file=sys.stderr)
        sys.exit(1)
    
    load_env()
    token = get_token()
    file_key = upload_file(token, file_path, file_name)
    result = send_file_message(token, chat_id, file_key)
    print(f"✅ Sent: {file_name} ({os.path.getsize(file_path)} bytes) -> chat {chat_id}")

if __name__ == "__main__":
    main()
