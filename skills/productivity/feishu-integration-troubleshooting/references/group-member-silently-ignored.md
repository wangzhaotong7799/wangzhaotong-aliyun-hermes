# Group Member Silently Ignored — Real-World Diagnosis

## Situation

A Feishu group existed with the bot and one authorized user (`ou_b13ee47717bdd2c2627dcdd08c8dda05`). A new user named 麒麟 (Qilin/Lin) was added to the group. When they sent messages, the bot never responded.

## Diagnosis Steps (with real log output)

### Step 1: Check the allowlist

```bash
cat ~/.hermes/.env | grep FEISHU_ALLOWED_USERS
```

Result:
```
FEISHU_ALLOWED_USERS=ou_b13ee47717bdd2c2627dcdd08c8dda05
```

Only one user — 麒麟 was not in the list.

### Step 2: Search gateway logs for the new user

```bash
grep "sender=user:" ~/.hermes/logs/gateway.log | tail -20
```

Result: **Zero entries for 麒麟**. All messages in the log were from `ou_b13ee47717bdd2c2627dcdd08c8dda05`.

No "Unauthorized user" warnings either — the gateway silently dropped 麒麟's group messages without any log trace.

### Step 3: Confirm channel_directory.json (group membership)

```json
{
  "feishu": [
    {
      "id": "oc_10d032f2e5b7b86d660945627d981888",
      "type": "dm"
    },
    {
      "id": "oc_9f433716bb8afe94566f177089e4f8f7",
      "name": "用户657799",
      "type": "group"
    }
  ]
}
```

The group `oc_9f433716bb8afe94566f177089e4f8f7` was already registered. The bot was in the group. The issue was purely the allowlist.

## Root Cause

The `FEISHU_ALLOWED_USERS` filter runs **before** the logging layer for group messages. Unlike DM messages (which may produce a "Unauthorized user: ou_xxx" warning in logs), **group messages from unallowed users are completely silently dropped**.

This means:
- No log entry
- No warning
- No error
- No way to detect the problem from logs alone — you must check the `.env` config explicitly.

## Resolution

Until the new user's open_id is added to `FEISHU_ALLOWED_USERS`, they cannot interact with the bot in any channel (DM or group).

## Key Takeaway

"Bot doesn't respond to new group member" → always check `FEISHU_ALLOWED_USERS` first. The absence of any log warning does **not** mean the message was processed.
