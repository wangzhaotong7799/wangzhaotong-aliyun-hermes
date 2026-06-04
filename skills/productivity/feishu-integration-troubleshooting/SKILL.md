---
name: feishu-integration-troubleshooting
description: Troubleshoot and set up Feishu (Lark) integration with Hermes Agent - pairing, gateway configuration, and authorization issues
tags:
  - feishu
  - lark
  - gateway
  - messaging
  - integration
  - troubleshooting
---

# Feishu Integration Troubleshooting

Complete guide to setting up and troubleshooting Feishu (Lark) integration with Hermes Agent. Covers pairing, gateway configuration, authorization issues, and common pitfalls.

## When to Use This Skill

Use this skill when:
- Setting up Feishu integration for the first time
- Encountering "Unauthorized user" errors in gateway logs
- Gateway fails to start after Feishu configuration
- Need to verify pairing status or troubleshoot connection issues

## Prerequisites

1. **Feishu Developer Account**: App ID and App Secret configured
2. **Environment Variables** already set:
   ```bash
   FEISHU_APP_ID=cli_xxxxxxxxxxxx
   FEISHU_APP_SECRET=xxxxxxxxxxxx
   ```

## Step-by-Step Setup

### 1. Verify Pairing Status

Check if pairing code has been successfully processed:

```bash
# Check pairing directory
ls -la ~/.hermes/pairing/

# View pending pairing file
cat ~/.hermes/pairing/feishu-pending.json
```

Expected output shows user details:
```json
{
  "PAIRING_CODE": {
    "user_id": "ou_xxxxxxxxxxxx",
    "user_name": "用户名",
    "created_at": 1776836007.4106693
  }
}
```

**Note**: The pairing code (e.g., `6JWF4ZWT`) becomes the key in the JSON file. If you see your code as a key with user details, pairing was successful.

**Troubleshooting pairing**:
- If file doesn't exist: Pairing hasn't completed or code was invalid
- If file exists but empty: Pairing process was interrupted
- If user_id is present: Pairing successful, proceed to gateway setup

### 2. Check Gateway Status

```bash
# Check if gateway is running
hermes gateway status

# View gateway logs (preferred — has full detail from current session)
tail -30 ~/.hermes/logs/gateway.log

# Also check systemd status for exit codes / signals
systemctl --user status hermes-gateway --no-pager | head -15
```

**Key distinction:** User systemd services (`systemctl --user`) may not write to the system journal (`journalctl`). If `journalctl -u hermes-gateway` returns "No entries", use `~/.hermes/logs/gateway.log` instead — it's always populated when the gateway runs.

### 3. Common Issues and Solutions

#### Issue 1: "Unauthorized user" warnings

**Symptoms**:
```
WARNING gateway.run: Unauthorized user: ou_xxxxxxxxxxxx (用户名) on feishu
WARNING gateway.run: No user allowlists configured. All unauthorized users will be denied.
```

**Understanding the issue**: Even with successful pairing, users need explicit authorization to interact with the gateway. This is a security feature.

**Sub-issue 1a: New group member silently ignored (no log warning)**

**Symptom**: A new user is added to an existing group chat that already contains the bot. The new user sends messages but the bot never responds. **Unlike DM scenarios, no "Unauthorized user" warning appears in the logs** — the gateway silently drops the message at the platform layer before it reaches the log filter.

**Diagnosis**:
```bash
# 1. Check the allowlist — does it include this user?
cat ~/.hermes/.env | grep FEISHU_ALLOWED_USERS
# If this only lists the original user(s), the new member is blocked

# 2. Search logs for any trace of the new user's messages
grep "sender=user:" ~/.hermes/logs/gateway.log | grep -v "ou_b13ee47717bdd2c2627dcdd08c8dda05" | tail -10
# If no results, the messages are being silently dropped before logging
```

**Root cause**: The `FEISHU_ALLOWED_USERS` filter runs at the platform layer inside the gateway. When a message arrives from an unallowed user in a group, the gateway acknowledges the webhook event (to avoid retries) but *never passes it to the processing pipeline* — hence no log entry or warning. DMs from unallowed users may produce a log warning, but **group messages are completely silent**.

**Fix**: Get the new user's Feishu open_id (see "How to get a user's open_id" below) and add it to `FEISHU_ALLOWED_USERS`.

**How to get a new user's open_id**:
1. **Best approach**: Ask the user to send a DM to the bot. Even though it will be rejected, check the gateway log for the rejection entry that includes their open_id:
   ```bash
   tail -20 ~/.hermes/logs/gateway.log | grep "Unauthorized user"
   ```
   If logging is configured for unauthorized DMs, the open_id will appear there.

2. **Fallback**: Check Feishu Admin Console → Members → find the user → view their profile. The open_id is typically shown in member details or can be retrieved via the Feishu Open API contact query endpoint.

3. **Last resort**: Temporarily set `GATEWAY_ALLOW_ALL_USERS=true` in `.env`, restart the gateway, have the user send one message, capture their open_id from the log, then revert to per-user allowlisting:
   ```bash
   # After getting the message logged, grep for the new sender
   grep "sender=user:" ~/.hermes/logs/gateway.log | tail -5
   # Update .env to add the new open_id
   sed -i 's/FEISHU_ALLOWED_USERS=ou_old/FEISHU_ALLOWED_USERS=ou_old,ou_new/' ~/.hermes/.env
   # Remove GATEWAY_ALLOW_ALL_USERS and restart
   sed -i '/GATEWAY_ALLOW_ALL_USERS/d' ~/.hermes/.env
   hermes gateway restart
   ```
   ⚠️ **Risk**: While `GATEWAY_ALLOW_ALL_USERS=true` is active, ANY user in any group can interact with the bot. Gate this operation tightly — it should only be open for seconds, not minutes.

**Solution**: Configure user authorization:

1. **Option A (Recommended)**: Add specific user to allowlist in `.env`:
   ```bash
   # Edit .env file and add:
   FEISHU_ALLOWED_USERS=ou_xxxxxxxxxxxx
   ```

2. **Option B**: Allow all users (use with caution for testing):
   ```bash
   # Edit .env file and add:
   GATEWAY_ALLOW_ALL_USERS=true
   ```

3. **Option C**: Platform-specific allow all (more secure than global):
   ```bash
   # Edit .env file and add:
   FEISHU_ALLOW_ALL_USERS=true
   ```

**Important**: After modifying `.env`, you must restart the gateway:
```bash
hermes gateway restart
# OR
systemctl --user restart hermes-gateway
```

**Verification**: Check gateway logs after restart:
```bash
journalctl -u hermes-gateway --since "1 minute ago" | grep -i "allow"
```
Should show gateway reading the new configuration.

#### Issue 6: Bot replies in group chats only visible to sender

**Symptoms**:
- The user who @-mentioned the bot can see the reply in the group
- Other group members see nothing from the bot
- Gateway logs show successful delivery (`Sending response (...) to oc_...`)

**Root cause**: Gateway sends responses with `reply_to=event.message_id`, making the Feishu adapter use `message.reply()`. Feishu's bot `message.reply()` in groups **defaults to private reply** — only the original sender sees it.

**Diagnosis**:
```bash
tail -20 ~/.hermes/logs/gateway.log | grep "Sending response"
# "oc_" prefix in the target = group chat
```

**Fix**: Add a check in `_feishu_send_with_retry()` to strip `reply_to` for group chats:
```python
if chat_id and chat_id.startswith("oc_"):
    reply_to = None
```
This forces `message.create()` instead of `message.reply()`, making the message visible to everyone. Restart after fix: `hermes gateway restart`.

**Scope**: Place in `_feishu_send_with_retry()` (lowest send layer) so it covers all message types (text, image, file, voice, video). Feishu API behavior — other platforms like Telegram handle `reply_to` differently.

#### Issue 8: Group member @mentions bot — bot sees nothing in logs

**Symptoms**:
- You (app creator) can @mention the bot in a group and get replies
- A different group member @mentions the bot — no response
- Gateway logs show **no inbound entries** for that user's messages at all
- No reject/warning/error in logs

**Root cause**: Feishu Open Platform's event subscription setting **"消息接收模式"** (message reception mode) defaults to **"仅应用创建者"** (app creator only). Messages from other users' @mentions are silently dropped by Feishu's servers before reaching your gateway.

**Diagnosis**:
```bash
# Check that the messages truly don't arrive — search for the group's inbound entries
grep "Inbound group message.*chat_id=oc_" ~/.hermes/logs/gateway.log | tail -20
# If ALL messages are from the same sender (ou_b13ee47717...), others are being filtered upstream
```

**Fix**: Change the Feishu App's event subscription setting:
1. Go to https://open.feishu.cn/app/ → your app
2. **事件订阅** → `im.message.receive_v1` → 配置 → **消息接收模式**
3. Change from `仅应用创建者` to `所有人`
4. Save and restart gateway: `hermes gateway restart`

See `references/feishu-open-platform-event-subscription.md` for full details.

#### Issue 9: Want to open bot to all group members without adding each OpenID

**Instead of** adding every user's OpenID to `FEISHU_ALLOWED_USERS`, use per-group rules in `config.yaml`:

```yaml
platforms:
  feishu:
    group_rules:
      oc_xxxxxxxxxxxx:
        policy: open
        require_mention: true
```

This allows anyone in that group to @mention the bot, without modifying `.env`.

See `references/feishu-group-rules-config.md` for all policy options.

#### Issue 7: Gateway fails to start (Python version)

**Symptoms**: Gateway exits with status 75 or Python compatibility errors like:
```
TypeError: unsupported operand type(s) for |: 'type' and 'NoneType'
```

**Check Python version**:
```bash
python3 --version
```

**Solution**: Ensure Python 3.8+ is available:

```bash
# Check for newer Python versions
which python3.11 || which python3.10 || which python3.9 || which python3.8

# The gateway should use the virtual environment's Python
cd ~/.hermes/hermes-agent
./venv/bin/python --version

# If system Python is too old (3.6), the gateway service may fail
# Check the actual error in logs:
journalctl -u hermes-gateway --since "1 minute ago" | tail -20
```

**Additional Fix**: If gateway fails due to Python 3.6 compatibility:
1. Check if the service is using the correct Python
2. Manually start gateway with the venv Python for debugging:
   ```bash
   cd ~/.hermes/hermes-agent
   ./venv/bin/python -m hermes_cli.main gateway run --replace 2>&1 | head -50
   ```

#### Issue 3: No messaging targets found

**Symptoms**: `send_message` returns "No messaging platforms connected"

**Solution**: Verify gateway is connected to Feishu:

```bash
# Check gateway state file
cat ~/.hermes/gateway_state.json | python3 -c "import sys, json; data=json.load(sys.stdin); print(json.dumps(data.get('platforms', {}).get('feishu', {}), indent=2))"
```

Should show:
```json
{
  "state": "connected",
  "error_code": null,
  "error_message": null,
  "updated_at": "2026-04-22T05:29:24.970706+00:00"
}
```

**Important**: The gateway state file is stale once the gateway is killed/restarted. If `state` shows "connected" but the gateway is down, the file wasn't updated before exit. Always verify with systemd status first.

#### Issue 4: Gateway killed (SIGKILL) — service died unexpectedly

**Symptoms**:
```bash
systemctl --user status hermes-gateway --no-pager | head -10
```
Shows:
```
Active: failed (Result: signal) since ...
Main PID: 258125 (code=killed, signal=KILL)
... Failed with result 'signal'.
```

**Root causes**:
1. **OOM Killer** — If memory is exhausted, the kernel sends SIGKILL to the largest process. Check `dmesg | grep -i oom` for evidence.
2. **Collateral damage** — Another operation (e.g., a shell script, `hermes gateway restart` from a running CLI session) may kill child processes that include the gateway. Look for "Shutdown diagnostic — other hermes processes running" in `~/.hermes/logs/gateway.log` to see what was running alongside.
3. **Systemctl kill cascade** — When systemd receives a stop/restart command, it sends SIGTERM then SIGKILL to the main process and all child processes.

**Diagnostic steps**:
```bash
# 1. Check for OOM events
dmesg | grep -i "oom\|killed process" | tail -5

# 2. Read the gateway log around the crash time
grep -n "SIGTERM\|SIGINT\|Shutdown diagnostic\|signal=KILL" ~/.hermes/logs/gateway.log | tail -10

# 3. Check if .env credentials survived (see Issue 5)
```

**Resolution**:
```bash
# Simply restart — the gateway will recover
systemctl --user restart hermes-gateway

# Then verify it's running and check for platform connection
sleep 3 && systemctl --user status hermes-gateway --no-pager | head -5
tail -10 ~/.hermes/logs/gateway.log
```

#### Issue 5: Gateway starts but says "No messaging platforms enabled"

**Symptoms** in `~/.hermes/logs/gateway.log`:
```
WARNING gateway.run: No messaging platforms enabled.
```

The gateway runs but reports no platforms. Root cause: **Feishu credentials are missing from `~/.hermes/.env`**.

**When this happens**:
- `.env` gets overwritten during other operations (e.g., CLI setup wizards, config changes)
- `.env` gets truncated by `write_file` operations with incomplete content
- Manual editing accidentally removes the Feishu lines

**Required environment variables in `.env`**:
```bash
FEISHU_APP_ID=cli_xxxxxxxxxxxx
FEISHU_APP_SECRET=xxxxxxxxxxxx
GATEWAY_ALLOW_ALL_USERS=true        # or FEISHU_ALLOWED_USERS=ou_xxxxxxxxxxxx
```

**Resolution**:
```bash
# 1. Check what's actually in .env
cat ~/.hermes/.env

# 2. If Feishu vars are missing, add them. Get credentials from:
#    - Feishu Developer Console: https://open.feishu.cn/app
#    - Backup at ~/.hermes/.env.bak or similar
#    - Or re-create the Feishu app if lost

# 3. Restart gateway after fixing
systemctl --user restart hermes-gateway
sleep 3 && tail -10 ~/.hermes/logs/gateway.log
```

**Expected success log**:
```
INFO gateway.run: Enabled platforms: feishu
[Lark] [INFO] connected to wss://msg-frontier.feishu.cn/ws/v2?
```

**Prevention**: Keep a backup of Feishu credentials in a dedicated config directory (e.g., `~/.hermes/hermes_config/.env.backup` or a git-tracked config repo) so they can be restored if `.env` is overwritten.

### 4. Manual Gateway Start (Debug Mode)

If automatic startup fails, run gateway manually for debugging:

```bash
# Stop systemd service
systemctl --user stop hermes-gateway

# Start manually with debug output
cd ~/.hermes/hermes-agent
./venv/bin/python -m hermes_cli.main gateway run --replace
```

Look for connection success message:
```
[Lark] [INFO] connected to wss://msg-frontier.feishu.cn/ws/v2?...
```

**Common manual start issues**:
1. **ModuleNotFoundError**: If you see `ModuleNotFoundError: No module named 'yaml'`, the virtual environment may not be activated or dependencies missing
2. **Python version errors**: If using system Python 3.6, switch to venv Python
3. **Permission errors**: Ensure you have read/write access to `~/.hermes/` directory

**Alternative manual start** (if venv Python has issues):
```bash
# Use absolute path to venv Python
/root/.hermes/hermes-agent/venv/bin/python -m hermes_cli.main gateway run --replace
```

### 5. Testing the Connection

Once gateway is running:

1. **Check service status**:
   ```bash
   systemctl --user status hermes-gateway
   ```

2. **Monitor gateway logs**:
   ```bash
   # Follow logs for 10 seconds
   timeout 10 journalctl -u hermes-gateway -f
   ```

3. **Send test message from Feishu**:
   - Open Feishu app
   - Find Hermes Agent bot
   - Send message: "测试" or "hello"

### 6. Complete Verification

Run comprehensive check:

```bash
#!/bin/bash
echo "=== Feishu Integration Check ==="

# 1. Check pairing
echo "1. Pairing status:"
if [ -f ~/.hermes/pairing/feishu-pending.json ]; then
    echo "   ✓ Pairing file exists"
    cat ~/.hermes/pairing/feishu-pending.json | python3 -c "import sys, json; data=json.load(sys.stdin); print('   Users:', list(data.keys()))"
else
    echo "   ✗ No pairing file"
fi

# 2. Check gateway
echo "2. Gateway status:"
if systemctl --user is-active hermes-gateway >/dev/null 2>&1; then
    echo "   ✓ Gateway is running"
else
    echo "   ✗ Gateway is not running"
fi

# 3. Check connection
echo "3. Feishu connection:"
if [ -f ~/.hermes/gateway_state.json ]; then
    CONNECTION=$(cat ~/.hermes/gateway_state.json | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('platforms', {}).get('feishu', {}).get('state', 'unknown'))" 2>/dev/null)
    echo "   Connection state: $CONNECTION"
fi

echo "=== Check Complete ==="
```

### 7. Sending Messages: open_id vs chat_id

**Key distinction when using `send_message(target="feishu:...")`:**
- `feishu:ou_<open_id>` → ❌ Error `[230001] invalid receive_id`
- `feishu:oc_<chat_id>` → ✅ Works

The user's pairing info stores their **open_id** (`ou_` prefix), but `send_message` requires a **chat_id** (`oc_` prefix) — even for DMs.

**How to find the correct chat_id:**
```bash
cat ~/.hermes/channel_directory.json
# Look under platforms.feishu — the first entry is your DM chat:
# {
#   "id": "oc_xxxxxxxxxxxx",
#   "type": "dm"
# }
```

**Test before sending important messages:**
Send a short test message first with the chat_id before sending long reports or file links. This avoids losing work when the target format is wrong.

**MEDIA attachments limitation**: `send_message` with `MEDIA:/path/to/file` in the message body does NOT work for Feishu. When a MEDIA reference is included, the Feishu adapter silently omits the attachment. The text content still sends successfully, but the file is dropped. This differs from Telegram/Discord/Signal which all support inline MEDIA attachments.

**Workarounds for file delivery via Feishu:**

1. **Rich text content** — send the document content as a formatted message instead of an attachment (most reliable)
2. **Feishu Drive upload** — use the Feishu Open API to upload files directly to Feishu Drive (requires tenant_access_token):
   ```bash
   # Get token
   TOKEN=$(curl -s -X POST 'https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal' \
     -H 'Content-Type: application/json' \
     -d '{"app_id":"YOUR_APP_ID","app_secret":"YOUR_APP_SECRET"}' | python3 -c "import sys,json;print(json.load(sys.stdin).get('tenant_access_token',''))")
   
   # Upload file to drive
   curl -s -X POST 'https://open.feishu.cn/open-apis/im/v1/files' \
     -H "Authorization: Bearer $TOKEN" \
     -F "file_type=stream" \
     -F "file_name=report.docx" \
     -F "file=@/path/to/file.docx"
   ```
3. **Link to file** — if the file is on a public server, send a download link instead
4. **Image/PDF via message.create API** — the Feishu message.create endpoint supports direct file upload with multipart/form-data, but `send_message` doesn't expose this API

**Note:** For group chats (delivery targets like `oc_99961a56e530e89f7e369cd6ecb50218` in cron jobs), the Bot must be added to the group first, or you'll get error `[230002] Bot/User can NOT be out of the chat.`

#### Direct API Fallback (When `send_message` Tool Is Unavailable)

When running as a cron job or in contexts where the `send_message` tool is not in your toolset, you can use the Feishu Open API directly via Python's `urllib` (no external dependencies needed):

1. Get a `tenant_access_token` from the auth endpoint (using `FEISHU_APP_ID` + `FEISHU_APP_SECRET` from `.env`)
2. Send the message via `im/v1/messages` with `receive_id_type=chat_id`

**⚠️ Secret extraction caveat**: When reading `.env` to get credentials, remember that `read_file` masks secrets. Use raw byte reading (see Pitfall #10) to get the complete `FEISHU_APP_SECRET`.

**Multi-channel retry**: Different chats have different bot membership. If one `oc_` chat_id returns 230002, try other channels (DM, other groups) from `channel_directory.json`. The DM channel (`type: "dm"`) is the most reliable — it's created automatically when the user first pairs with the bot.

See `references/direct-api-messaging.md` for complete Python code and error handling.

## Common Pitfalls

1. **Python Version**: Hermes Agent requires Python 3.8+. System Python 3.6 will fail.
2. **Virtual Environment**: Gateway should use the venv Python, not system Python.
3. **User Authorization**: New users need to be added to allowlist via `FEISHU_ALLOWED_USERS`.
4. **Service Permissions**: User systemd services may need linger enabled.
5. **Network Connectivity**: Ensure outbound connections to Feishu servers are allowed.
6. **`.env` file integrity**: Feishu credentials in `.env` can be silently lost when:
   - Another tool/command overwrites `.env` with a template or incomplete content
   - The `write_file` tool truncates the file before writing new content
   - A setup wizard regenerates `.env` without preserving existing entries
   **Mitigation**: Keep credentials in a version-controlled backup config directory.
7. **Gateway.log vs journalctl**: For user-systemd services, `journalctl --user` may return "No entries". Always use `~/.hermes/logs/gateway.log` as the primary log source.
8. **Stale gateway_state.json**: The state file is not updated on crash/kill. If it shows "connected" but the gateway is down, the data is stale. Trust `systemctl --user status` over the state file.
9. **`.env` file secret masking by read_file**: When you use `read_file` to view `~/.hermes/.env`, the system automatically masks sensitive values by replacing the middle portion with `...`. For example, `FEISHU_APP_SECRET=JaKXB3IwqrsgAsCGp3cTPeUWjNvMfKk3` is displayed as `FEISHU_APP_SECRET=JaKXB3...fKk3`. This means you **cannot copy-paste the secret** from the read_file output — it's incomplete.
    
    **Workaround**: Read the file as raw bytes and decode manually:
    ```python
    import os
    env_path = os.path.expanduser("~/.hermes/.env")
    with open(env_path, 'rb') as f:
        raw = f.read()
    for line in raw.split(b'\n'):
        if b'FEISHU_APP_SECRET' in line:
            decoded = line.decode('utf-8')
            secret = decoded.split('=', 1)[1]
            # secret now has the COMPLETE value
    ```
    
    This applies to ALL API keys in `.env` (not just Feishu). When you need the actual value, always use raw byte reading.
    
    **Mitigation**: Keep a backup of Feishu credentials in a git-tracked config repo so you can always look up the original secret without needing to extract it from `.env`.

## Troubleshooting Flowchart

```
Start → Check pairing file → Exists? → No → Need new pairing code
                    ↓ Yes
            Check gateway status → 
                Running? → No → Check systemd result → 
                    signal=KILL (SIGKILL) → Check OOM / collateral damage → Restart
                    exit code 75 → Python version issue → Use venv
                    Stopped → Start gateway → Verify credentials in .env
                ↓ Yes
            Check log for platform → 
                "No messaging platforms enabled" → Feishu credentials missing from .env → Add them → Restart
                "Enabled platforms: feishu" → Check connection state
                ↓
            Check connection state → 
                "connected to wss://msg-frontier.feishu.cn" → ✓
                "Unauthorized user" → Configure allowlist → Restart
                Anything else → Check logs for specific error
                    ↓
            Test with Feishu message → Works? → No → Check authorization
                    ↓ Yes
            Integration Complete
```

## Reference Files

- `references/credential-loss-sigkill-recovery.md` — Full diagnostic walkthrough of a real incident where the gateway was killed by SIGKILL and Feishu credentials were lost from `.env`. Useful as a concrete pattern to follow when investigating "Feishu not working".
- `references/group-member-silently-ignored.md` — Walkthrough of diagnosing a new group member whose messages were silently dropped by the allowlist filter. Covers the key insight: group messages from unallowed users produce no log warning, unlike DMs.
- `references/feishu-open-platform-event-subscription.md` — Guide to Feishu Open Platform event subscription settings, particularly "消息接收模式" which controls whether @mentions from non-creator users reach the gateway. Includes permission checklist and step-by-step configuration instructions.
- `references/feishu-group-rules-config.md` — Per-group access policy configuration via config.yaml `group_rules`. Covers all policy options (open, disabled, admin_only, allowlist, blacklist) and how they interact with the global `FEISHU_ALLOWED_USERS` setting.
- `references/direct-api-messaging.md` — Sending Feishu messages via direct Open API (Python/urllib) as a fallback when the `send_message` tool is not available. Covers token acquisition, chat_id determination, error codes (230001/230002), and multi-channel fallback strategy.

## Related Skills

- `github-auth` - Similar OAuth/API key configuration patterns
- `send_message` - General messaging platform integration