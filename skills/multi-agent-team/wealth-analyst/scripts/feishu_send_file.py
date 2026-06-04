#!/root/.hermes/hermes-agent/venv/bin/python3
"""飞书通用文件发送脚本 - 上传任意文件并发送为文件消息

用法:
  python3 feishu_send_file.py <文件路径> <chat_id>

示例:
  python3 feishu_send_file.py /tmp/报告.txt oc_10d032f2e5b7b86d660945627d981888

依赖: 无需额外依赖，使用标准库 urllib
环境变量: FEISHU_APP_ID, FEISHU_APP_SECRET（从 ~/.hermes/.env 自动读取）
"""
import json, os, sys, urllib.request


def get_env(key):
    val = os.environ.get(key)
    if val:
        return val
    env_path = os.path.expanduser("~/.hermes/.env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line.startswith(f"{key}="):
                    return line.split("=", 1)[1]
    return None


def get_token():
    app_id = get_env("FEISHU_APP_ID")
    app_secret = get_env("FEISHU_APP_SECRET")
    if not app_id or not app_secret:
        print("请设置 FEISHU_APP_ID 和 FEISHU_APP_SECRET")
        sys.exit(1)
    payload = json.dumps({"app_id": app_id, "app_secret": app_secret}).encode()
    req = urllib.request.Request(
        "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
        data=payload, headers={"Content-Type": "application/json"}
    )
    resp = json.loads(urllib.request.urlopen(req).read())
    token = resp.get("tenant_access_token")
    if not token:
        print(f"获取 token 失败: {resp}")
        sys.exit(1)
    return token


def upload_file(token, file_path):
    file_name = os.path.basename(file_path)
    ext = os.path.splitext(file_name)[1].lower()
    ext_map = {".txt": "stream", ".md": "stream", ".pdf": "pdf", ".doc": "doc",
               ".docx": "doc", ".jpg": "stream", ".png": "stream", ".mp4": "stream"}
    file_type = ext_map.get(ext, "stream")

    with open(file_path, "rb") as f:
        file_data = f.read()

    boundary = "----FormBoundary7MA4YWxkTrZu0gW"
    body_parts = [
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"file_type\"\r\n\r\n{file_type}\r\n".encode(),
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"file_name\"\r\n\r\n{file_name}\r\n".encode(),
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{file_name}\"\r\nContent-Type: application/octet-stream\r\n\r\n".encode(),
        file_data,
        f"\r\n--{boundary}--\r\n".encode(),
    ]
    body = b"".join(body_parts)

    req = urllib.request.Request(
        "https://open.feishu.cn/open-apis/im/v1/files", data=body,
        headers={"Authorization": f"Bearer {token}",
                 "Content-Type": f"multipart/form-data; boundary={boundary}"}
    )
    resp = json.loads(urllib.request.urlopen(req).read())
    if resp.get("code") != 0:
        print(f"上传失败: {resp}")
        sys.exit(1)
    file_key = resp["data"]["file_key"]
    print(f"上传成功: file_key={file_key}")
    return file_key


def send_file_message(token, chat_id, file_key):
    content = json.dumps({"file_key": file_key}, ensure_ascii=False)
    payload = json.dumps({"receive_id": chat_id, "msg_type": "file", "content": content},
                         ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=chat_id",
        data=payload,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json; charset=utf-8"}
    )
    resp = json.loads(urllib.request.urlopen(req).read())
    if resp.get("code") == 0:
        print(f"文件已投递到 {chat_id}")
    else:
        print(f"发送失败: {resp.get('msg')} (code={resp.get('code')})")
    return resp


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    file_path = sys.argv[1]
    if not os.path.exists(file_path):
        print(f"文件不存在: {file_path}")
        sys.exit(1)
    chat_id = sys.argv[2] if len(sys.argv) > 2 else "oc_10d032f2e5b7b86d660945627d981888"
    token = get_token()
    file_key = upload_file(token, file_path)
    send_file_message(token, chat_id, file_key)
