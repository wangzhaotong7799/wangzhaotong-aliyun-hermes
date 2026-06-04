# Direct Feishu API Messaging (Fallback When send_message Is Unavailable)

When the `send_message` tool is not available in your toolset (e.g., running as a cron job), you can use the Feishu Open API directly to send text messages.

## Full Python Workflow

```python
import json, urllib.request, urllib.error

# 1. Get tenant_access_token
app_id = "cli_xxxxxxxxxxxx"
app_secret = "xxxxxxxxxxxxxxxxxxxxxxxxxxxxx"

token_url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
token_data = json.dumps({"app_id": app_id, "app_secret": app_secret}).encode('utf-8')
req = urllib.request.Request(token_url, data=token_data, headers={"Content-Type": "application/json"})
resp = urllib.request.urlopen(req)
token_result = json.loads(resp.read().decode('utf-8'))
token = token_result["tenant_access_token"]  # code=0 means success

# 2. Send text message to a chat
chat_id = "oc_xxxxxxxxxxxx"  # Get from channel_directory.json
msg_text = "Your message here"

msg_content = json.dumps({"text": msg_text})
msg_url = "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=chat_id"
msg_data = json.dumps({
    "receive_id": chat_id,
    "msg_type": "text",
    "content": msg_content
}).encode('utf-8')

req2 = urllib.request.Request(
    msg_url, data=msg_data,
    headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }
)
resp2 = urllib.request.urlopen(req2)
result = json.loads(resp2.read().decode('utf-8'))
# code=0 means success
```

## Determining chat_id

Read `~/.hermes/channel_directory.json`:

```json
{
  "platforms": {
    "feishu": [
      {"id": "oc_10d032f2e5b7b86d660945627d981888", "name": "oc_...", "type": "dm"},
      {"id": "oc_9f433716bb8afe94566f177089e4f8f7", "name": "用户657799", "type": "group"}
    ]
  }
}
```

- `type: "dm"` — Direct message to the user who paired with the bot
- `type: "group"` — Group chat the bot has joined

## Error Handling

| Error Code | Message | Cause | Fix |
|---|---|---|---|
| 230002 | Bot/User can NOT be out of the chat | Bot is not a member of the target group | Add bot back to the group, or use a different chat_id |
| 230001 | invalid receive_id | Wrong chat_id format (e.g., using open_id instead of chat_id) | Use `oc_` prefix chat_id, not `ou_` prefix open_id |

## Multi-Channel Fallback Strategy

When one chat fails (e.g., bot was removed from a group), try all available chats:

```python
chat_ids_to_try = [
    ("DM", "oc_xxx_dm_channel"),
    ("Group A", "oc_xxx_group_a"),
    ("Group B", "oc_xxx_group_b"),
]

for name, chat_id in chat_ids_to_try:
    # attempt send_message or direct API
    # log success/failure for each
```

This is useful for cron jobs where reliable delivery matters — even if the bot was removed from one group, it may still reach the user via another channel.
